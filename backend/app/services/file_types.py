"""
File type helpers for uploaded notebook workspace files.

Why this exists:
- We need robust detection for multi-part extensions like `.nii.gz` (NIfTI, commonly gzipped).
- We want a stable, semantic `type` field for the frontend and LLM context (e.g., `image`, `dicom`, `nifti`)
  instead of leaking raw extensions everywhere.

This module intentionally does NOT attempt to parse file contents (no pydicom/nibabel dependency).
"""

from __future__ import annotations

from pathlib import Path


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
}

DICOM_EXTENSIONS = {
    ".dcm",
    ".dicom",
}

# NIfTI is often stored as `.nii` or gzipped `.nii.gz`.
NIFTI_EXTENSIONS = {
    ".nii",
    ".nii.gz",
}


def get_effective_extension(filename: str) -> str:
    """
    Return the effective extension for a filename.

    Special-cases `.nii.gz` so we don't misclassify gzipped NIfTI files as just `.gz`.
    """
    name = (filename or "").strip().lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return Path(name).suffix.lower()


def classify_file_type(filename: str, *, is_h5_file: bool = False) -> str:
    """
    Classify a filename into a small, semantic set used across the app.

    Notes:
    - For H5/HDF5/H5AD we keep the original extension as the type (historical behavior).
    - For images we return `image`.
    - For DICOM we return `dicom`.
    - For NIfTI we return `nifti`.
    - Unknown/unsupported extensions return `other` (so the frontend stays stable).
    """
    ext = get_effective_extension(filename)
    if not ext:
        return "other"

    if is_h5_file:
        return ext.lstrip(".")

    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in DICOM_EXTENSIONS:
        return "dicom"
    if ext in NIFTI_EXTENSIONS:
        return "nifti"

    ext_no_dot = ext.lstrip(".")
    # Keep legacy types as-is for LLM preview logic (csv/tsv/json/yaml/yml/xlsx/xls/txt/md, etc.)
    if ext_no_dot in {
        "csv",
        "tsv",
        "json",
        "yaml",
        "yml",
        "xlsx",
        "xls",
        "txt",
        "md",
    }:
        return ext_no_dot

    return "other"

