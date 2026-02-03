"""
File context preview builders.

Goal
----
Digital Article's LLM is used to *generate code* that will read the full file at runtime.
Therefore, LLM context should contain a **compact, structured overview** of a file (schema + samples),
not the full file payload (which is token-expensive and often misleading).

This module implements "rendering-only" compaction per ADR 0003:
- We never truncate/compact the *runtime data ingest* (code execution reads full files).
- We may compact the *LLM prompt context* by providing structured summaries and small samples.
- Any compaction must be explicit via `#COMPACTION_NOTICE:` and logged at INFO.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class TokenEstimator:
    """
    Small wrapper around AbstractCore token estimation with a deterministic fallback.

    We intentionally keep estimation lightweight and avoid reading entire large files
    just to estimate tokens; callers may provide approximate inputs when appropriate.
    """

    def __init__(self) -> None:
        try:
            from abstractcore.utils.token_utils import estimate_tokens as _estimate_tokens  # type: ignore

            self._estimate_tokens = _estimate_tokens
            self._available = True
        except Exception:
            self._estimate_tokens = None
            self._available = False

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        if self._available and self._estimate_tokens is not None:
            try:
                return int(self._estimate_tokens(text))
            except Exception:
                # fall through to deterministic approximation
                pass
        # Deterministic approximation: ~4 chars/token (reasonable for English-ish text)
        return max(1, len(text) // 4)


@dataclass(frozen=True)
class SampleWindow:
    purpose: str
    byte_start: int
    byte_end: int
    text: str


class FileContextPreviewBuilder:
    """
    Builds compact-but-rich preview payloads for files injected into LLM context.

    The builder is configurable to keep tests fast and make behavior explicit.
    """

    def __init__(
        self,
        *,
        token_estimator: Optional[TokenEstimator] = None,
        # For "text-like" files, we always build an overview, but we may include full content for
        # very small files when it's cheap and helpful.
        max_full_content_tokens: int = 1500,
        # Parsing structured text (JSON/YAML) is only attempted below this byte threshold.
        max_structured_parse_bytes: int = 1_000_000,
        # Tabular: beyond this size, avoid full pandas reads.
        max_tabular_full_read_bytes: int = 15 * 1024 * 1024,
        # If file is under this size, compute a full sha256; otherwise use head+tail fingerprint.
        max_full_sha256_bytes: int = 5 * 1024 * 1024,
        # Sample window sizes (bytes)
        head_bytes: int = 8_192,
        tail_bytes: int = 8_192,
        mid_window_bytes: int = 6_144,
        mid_context_bytes: int = 1_024,
        # CSV tail sampling
        csv_tail_max_lines: int = 200,
    ) -> None:
        self._tokens = token_estimator or TokenEstimator()
        self._max_full_content_tokens = max_full_content_tokens
        self._max_structured_parse_bytes = max_structured_parse_bytes
        self._max_tabular_full_read_bytes = max_tabular_full_read_bytes
        self._max_full_sha256_bytes = max_full_sha256_bytes
        self._head_bytes = head_bytes
        self._tail_bytes = tail_bytes
        self._mid_window_bytes = mid_window_bytes
        self._mid_context_bytes = mid_context_bytes
        self._csv_tail_max_lines = csv_tail_max_lines

    # ---------------------------------------------------------------------
    # Shared helpers
    # ---------------------------------------------------------------------

    def build_identity(self, file_path: Path) -> Dict[str, Any]:
        st = file_path.stat()
        size = int(st.st_size)
        mtime = st.st_mtime

        fingerprint = self._fingerprint_sha256(file_path, size_bytes=size)
        return {
            "size_bytes": size,
            "mtime": mtime,
            "fingerprint": fingerprint,
        }

    def _fingerprint_sha256(self, file_path: Path, *, size_bytes: int) -> Dict[str, Any]:
        """
        Compute a stable fingerprint without necessarily reading the whole file.

        - Small files: full sha256.
        - Large files: sha256(head + NUL + tail + NUL + size_bytes).

        This is deterministic and cheap enough for listing contexts.
        """
        if size_bytes <= self._max_full_sha256_bytes:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 128), b""):
                    h.update(chunk)
            full = h.hexdigest()
            return {
                "algorithm": "sha256",
                "is_full_file_hash": True,
                "sha256": full,
                "sha256_prefix": full[:16],
            }

        head = b""
        tail = b""
        with open(file_path, "rb") as f:
            head = f.read(65_536)
            if size_bytes > 65_536:
                f.seek(max(0, size_bytes - 65_536))
                tail = f.read(65_536)

        h = hashlib.sha256()
        h.update(head)
        h.update(b"\x00")
        h.update(tail)
        h.update(b"\x00")
        h.update(str(size_bytes).encode("utf-8"))
        partial = h.hexdigest()
        return {
            "algorithm": "sha256",
            "is_full_file_hash": False,
            "basis": "head+tail+size_bytes",
            "sha256": partial,
            "sha256_prefix": partial[:16],
        }

    def _guess_text_encoding(self, head_bytes: bytes) -> str:
        # Minimal, dependency-free guessing. Prefer UTF-8; fall back to latin-1.
        try:
            head_bytes.decode("utf-8")
            return "utf-8"
        except Exception:
            return "latin-1"

    def _detect_newline_style(self, sample_bytes: bytes) -> Dict[str, Any]:
        # Note: this is a best-effort guess on a prefix, not a full-file scan.
        crlf = sample_bytes.count(b"\r\n")
        lf = sample_bytes.count(b"\n") - crlf
        cr = sample_bytes.count(b"\r") - crlf

        kinds = []
        if crlf:
            kinds.append("CRLF")
        if lf:
            kinds.append("LF")
        if cr:
            kinds.append("CR")

        if not kinds:
            style = "UNKNOWN"
        elif len(kinds) == 1:
            style = kinds[0]
        else:
            style = "MIXED"

        return {
            "style": style,
            "counts_prefix": {"CRLF": crlf, "LF": lf, "CR": cr},
        }

    def _read_window_at(
        self,
        file_path: Path,
        *,
        center_byte: int,
        file_size: int,
        purpose: str,
    ) -> SampleWindow:
        """
        Read a small, contiguous sample window around a byte offset.
        We align to the next newline when possible to avoid starting mid-line.
        """
        start = max(0, center_byte - self._mid_context_bytes)
        # Ensure we don't overflow
        max_read = self._mid_context_bytes + self._mid_window_bytes
        with open(file_path, "rb") as f:
            f.seek(start)
            blob = f.read(max_read)

        enc = self._guess_text_encoding(blob[:2048])
        # Try to align start to the next newline within the context section.
        pivot = min(self._mid_context_bytes, len(blob))
        nl = blob.find(b"\n", pivot)
        if nl != -1 and nl + 1 < len(blob):
            aligned = nl + 1
        else:
            aligned = pivot

        window_bytes = blob[aligned:]
        byte_start = start + aligned
        byte_end = min(file_size, byte_start + len(window_bytes))
        text = window_bytes.decode(enc, errors="replace")
        return SampleWindow(purpose=purpose, byte_start=byte_start, byte_end=byte_end, text=text)

    def _build_text_samples(self, file_path: Path, *, seed: int) -> Dict[str, Any]:
        st = file_path.stat()
        size = int(st.st_size)
        samples: List[SampleWindow] = []

        with open(file_path, "rb") as f:
            head_blob = f.read(self._head_bytes)
        enc = self._guess_text_encoding(head_blob)
        newline_info = self._detect_newline_style(head_blob)

        # Head sample
        samples.append(
            SampleWindow(
                purpose="head",
                byte_start=0,
                byte_end=min(size, len(head_blob)),
                text=head_blob.decode(enc, errors="replace"),
            )
        )

        # Tail sample
        if size > 0:
            tail_start = max(0, size - self._tail_bytes)
            with open(file_path, "rb") as f:
                f.seek(tail_start)
                tail_blob = f.read(self._tail_bytes)
            samples.append(
                SampleWindow(
                    purpose="tail",
                    byte_start=tail_start,
                    byte_end=min(size, tail_start + len(tail_blob)),
                    text=tail_blob.decode(enc, errors="replace"),
                )
            )

        # Deterministic mid windows (seeded by file fingerprint)
        if size > (self._head_bytes + self._tail_bytes + 1024):
            # Use a stable set of positions + a couple of seed-derived offsets.
            positions = [0.25, 0.5, 0.75]
            # Add two deterministic pseudo-random positions (bounded away from edges).
            # We avoid importing random to keep behavior simple and stable across Python versions.
            h = hashlib.sha256(str(seed).encode("utf-8")).digest()
            a = int.from_bytes(h[:4], "big") / 2**32
            b = int.from_bytes(h[4:8], "big") / 2**32
            positions.extend([0.15 + 0.7 * a, 0.15 + 0.7 * b])
            positions = sorted(set(positions))

            for i, p in enumerate(positions, start=1):
                center = int(size * p)
                samples.append(
                    self._read_window_at(
                        file_path,
                        center_byte=center,
                        file_size=size,
                        purpose=f"mid_{i}_at_{int(p*100)}pct",
                    )
                )

        compaction_notice = (
            "#COMPACTION_NOTICE: File content not fully included in LLM context. "
            "Only small deterministic samples (head/tail/mid windows) are shown. "
            "Generated runtime code must read the full file from disk.\n"
        )
        logger.info(compaction_notice.strip())
        return {
            "encoding_guess": enc,
            "newline": newline_info,
            "compaction_notice": compaction_notice,
            "samples": [
                {
                    "purpose": s.purpose,
                    "byte_start": s.byte_start,
                    "byte_end": s.byte_end,
                    "text": s.text,
                }
                for s in samples
            ],
        }

    # ---------------------------------------------------------------------
    # Text / Markdown / JSON / YAML previews
    # ---------------------------------------------------------------------

    def build_text_like_preview(self, file_path: Path, *, file_kind: str) -> Dict[str, Any]:
        """
        Build an overview for text-like files. `file_kind` should be one of:
        - text, markdown, json, yaml
        """
        identity = self.build_identity(file_path)
        fp = identity["fingerprint"]
        seed = int(fp.get("sha256_prefix", "0"), 16)

        # Approximate token estimate without reading whole file.
        approx_tokens = max(1, int(identity["size_bytes"]) // 4) if identity["size_bytes"] else 0

        overview: Dict[str, Any] = {
            "identity": identity,
            "approx_tokens": approx_tokens,
        }
        overview.update(self._build_text_samples(file_path, seed=seed))

        # For structured formats (JSON/YAML), attempt to parse small files to extract schema.
        if file_kind in {"json", "yaml"} and identity["size_bytes"] <= self._max_structured_parse_bytes:
            try:
                text = file_path.read_text(encoding=overview["encoding_guess"], errors="replace")
                if file_kind == "json":
                    data = json.loads(text)
                    overview["structure"] = self._json_structure_summary(data)
                else:
                    try:
                        import yaml  # type: ignore
                    except Exception:
                        yaml = None
                    if yaml is not None:
                        data = yaml.safe_load(text)
                        overview["structure"] = self._yaml_structure_summary(data)
                    else:
                        overview["structure"] = {"error": "pyyaml_not_installed"}
            except Exception as e:
                overview["structure"] = {"error": f"parse_failed: {e.__class__.__name__}: {e}"}
        elif file_kind == "markdown":
            overview["structure"] = self._markdown_structure_summary(file_path, encoding=overview["encoding_guess"])

        # Include full content only for very small files (cheap and occasionally helpful).
        # IMPORTANT: LLM prompt formatting should still prefer `overview` unless explicitly requested.
        full_content: Optional[str] = None
        if identity["size_bytes"] <= self._max_structured_parse_bytes:
            try:
                candidate = file_path.read_text(encoding=overview["encoding_guess"], errors="replace")
                if self._tokens.estimate(candidate) <= self._max_full_content_tokens:
                    full_content = candidate
            except Exception:
                full_content = None

        preview: Dict[str, Any] = {
            "file_type": file_kind,
            "overview": overview,
        }
        if full_content is not None:
            preview["full_content"] = full_content
            preview["include_full_content_in_llm_context"] = True
        else:
            preview["include_full_content_in_llm_context"] = False

        # Frontend/UI convenience fields
        preview["estimated_tokens"] = approx_tokens
        preview["is_large_file"] = approx_tokens >= 25_000
        return preview

    def _json_structure_summary(self, data: Any, *, max_depth: int = 3) -> Dict[str, Any]:
        def analyze(node: Any, depth: int) -> Dict[str, Any]:
            if depth >= max_depth:
                return {"type": type(node).__name__, "truncated": True}
            if isinstance(node, dict):
                keys = list(node.keys())
                props = {}
                for k in keys[:20]:
                    props[str(k)] = analyze(node.get(k), depth + 1)
                result: Dict[str, Any] = {"type": "object", "keys_count": len(keys), "properties": props}
                if len(keys) > 20:
                    result["additional_keys"] = len(keys) - 20
                return result
            if isinstance(node, list):
                item_types = Counter(type(x).__name__ for x in node[:50])
                items_schema = analyze(node[0], depth + 1) if node else {"type": "unknown"}
                return {
                    "type": "array",
                    "length": len(node),
                    "items_schema": items_schema,
                    "sample_item_types": dict(item_types),
                }
            return {"type": type(node).__name__, "example": str(node)[:80]}

        return analyze(data, 0)

    def _yaml_structure_summary(self, data: Any) -> Dict[str, Any]:
        # YAML can map to many Python types; reuse the JSON structure analyzer for readability.
        return self._json_structure_summary(data)

    def _markdown_structure_summary(self, file_path: Path, *, encoding: str) -> Dict[str, Any]:
        # Extract a heading outline from a bounded scan to avoid expensive full reads for large docs.
        max_bytes = min(int(file_path.stat().st_size), 512_000)  # 512KB scan cap
        with open(file_path, "rb") as f:
            blob = f.read(max_bytes)
        text = blob.decode(encoding, errors="replace")
        headings: List[Dict[str, Any]] = []
        for line in text.splitlines()[:10_000]:
            m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if m:
                headings.append({"level": len(m.group(1)), "title": m.group(2).strip()[:200]})
                if len(headings) >= 80:
                    break
        return {
            "type": "markdown",
            "headings": headings,
            "headings_truncated": len(headings) >= 80,
            "scan_bytes": max_bytes,
        }

    # ---------------------------------------------------------------------
    # Tabular previews (CSV/TSV)
    # ---------------------------------------------------------------------

    def build_tabular_preview(
        self,
        file_path: Path,
        *,
        sep: str,
        file_name: str,
        get_column_stats: Callable[[Any], Dict[str, Dict[str, Any]]],
        is_data_dictionary: Callable[[str, Any], bool],
    ) -> Dict[str, Any]:
        """
        Build a preview for CSV/TSV while attempting to avoid full reads on large files.

        Contract (existing):
        - rows, columns, shape, column_stats, sample_data, is_dictionary
        """
        import numpy as np
        import pandas as pd

        size_bytes = int(file_path.stat().st_size)
        sampling: Dict[str, Any] = {"mode": "full_read" if size_bytes <= self._max_tabular_full_read_bytes else "head+tail"}

        if size_bytes <= self._max_tabular_full_read_bytes:
            df_full = pd.read_csv(file_path, sep=sep)
            is_dictionary_flag = is_data_dictionary(file_name, df_full)
            if is_dictionary_flag:
                df_sample = df_full.replace({np.nan: None, np.inf: None, -np.inf: None})
            else:
                df_sample = df_full.head(20).replace({np.nan: None, np.inf: None, -np.inf: None})
            sample_records = self._df_to_clean_records(df_sample)
            return {
                "rows": len(df_full),
                "columns": [str(c) for c in df_full.columns.tolist()],
                "shape": [len(df_full), len(df_full.columns)],
                "column_stats": get_column_stats(df_full),
                "sample_data": sample_records,
                "is_dictionary": is_dictionary_flag,
                "sampling": sampling,
            }

        # Large file: avoid full read. Use head rows for stats + tail rows for some coverage.
        head_n = 5_000
        df_head = pd.read_csv(file_path, sep=sep, nrows=head_n)
        is_dictionary_flag = is_data_dictionary(file_name, df_head)
        columns = [str(c) for c in df_head.columns.tolist()]
        sampling["head_nrows"] = head_n

        # Tail sampling: take last N lines and parse with pandas using the known header.
        df_tail = self._read_csv_tail(file_path, sep=sep, columns=columns)
        tail_rows = int(len(df_tail)) if df_tail is not None else 0
        sampling["tail_rows"] = tail_rows
        sampling["tail_max_lines"] = self._csv_tail_max_lines

        # Build sample rows: stratified head+tail (deterministic).
        head_part = df_head.head(10)
        if df_tail is not None and len(df_tail) > 0:
            tail_part = df_tail.tail(10)
            df_sample = pd.concat([head_part, tail_part], ignore_index=True)
        else:
            df_sample = head_part

        df_sample = df_sample.replace({np.nan: None, np.inf: None, -np.inf: None})
        sample_records = self._df_to_clean_records(df_sample)

        # Rows: optionally estimate for moderate file sizes by counting newlines (cheap streaming).
        row_count: Optional[int] = None
        if size_bytes <= 50 * 1024 * 1024:  # 50MB
            row_count = self._count_tabular_rows_fast(file_path)
            sampling["rows_estimated_by"] = "newline_count"
        else:
            sampling["rows_estimated_by"] = "skipped_large_file"

        ncols = len(columns)
        shape_rows = row_count if row_count is not None else None
        sampling["column_stats_basis"] = f"head({head_n})"
        return {
            "rows": row_count,
            "columns": columns,
            "shape": [shape_rows, ncols],
            "column_stats": get_column_stats(df_head),
            "sample_data": sample_records[:20],
            "is_dictionary": is_dictionary_flag,
            "sampling": sampling,
        }

    def _df_to_clean_records(self, df) -> List[Dict[str, Any]]:
        import pandas as pd

        records: List[Dict[str, Any]] = []
        for record in df.to_dict("records"):
            clean_record = {str(k): (None if pd.isna(v) else v) for k, v in record.items()}
            records.append(clean_record)
        return records

    def _read_csv_tail(self, file_path: Path, *, sep: str, columns: List[str]):
        """
        Best-effort tail sampling for CSV/TSV.

        This is used ONLY for preview context; failures fall back gracefully.
        """
        import pandas as pd

        try:
            # Read last N lines in text mode (assume utf-8-ish; replacement is OK for preview).
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                tail = deque(f, maxlen=self._csv_tail_max_lines)
            if not tail:
                return None

            # If the header appears in the tail (small files), drop it to avoid duplicate header rows.
            header_line = sep.join(columns)
            tail_lines = [line for line in tail if line.strip() and line.strip() != header_line]
            if not tail_lines:
                return None

            payload = header_line + "\n" + "".join(tail_lines)
            return pd.read_csv(io.StringIO(payload), sep=sep)
        except Exception:
            return None

    def _count_tabular_rows_fast(self, file_path: Path) -> int:
        """
        Count data rows (excluding header) by counting newline characters.
        This is a best-effort estimator; it assumes one record per line.
        """
        #TRUNCATION_NOTICE: This is NOT used for ingest/query; only for preview metadata.
        count = 0
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                count += chunk.count(b"\n")
        # Subtract header line (best effort).
        return max(0, count - 1)

