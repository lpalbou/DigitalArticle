from __future__ import annotations

import io

import pytest

from backend.app.services.file_types import classify_file_type, get_effective_extension
from backend.app.services.upload_service import FileUploadService, UploadError, UploadLimits


def test_get_effective_extension_handles_nii_gz() -> None:
    assert get_effective_extension("brain.nii.gz") == ".nii.gz"
    assert get_effective_extension("BRAIN.NII.GZ") == ".nii.gz"


def test_classify_file_type_medical_imaging() -> None:
    assert classify_file_type("scan.dcm") == "dicom"
    assert classify_file_type("scan.dicom") == "dicom"
    assert classify_file_type("brain.nii") == "nifti"
    assert classify_file_type("brain.nii.gz") == "nifti"


def test_classify_file_type_images() -> None:
    assert classify_file_type("img.png") == "image"
    assert classify_file_type("img.JPG") == "image"
    assert classify_file_type("img.tiff") == "image"


def test_classify_file_type_unknown_is_other() -> None:
    assert classify_file_type("report.pdf") == "other"
    assert classify_file_type("noext") == "other"


def test_sanitize_filename_strips_paths(tmp_path) -> None:
    svc = FileUploadService(tmp_path)
    assert svc.sanitize_filename("foo/bar.png") == "bar.png"
    assert svc.sanitize_filename(r"C:\foo\bar.dcm") == "bar.dcm"


def test_resolve_destination_rejects_escape(tmp_path) -> None:
    svc = FileUploadService(tmp_path)
    with pytest.raises(UploadError):
        svc.resolve_destination("../evil.txt")


def test_save_stream_writes_file_and_sanitizes_name(tmp_path) -> None:
    svc = FileUploadService(tmp_path)
    stored_name, bytes_written = svc.save_stream("../evil.txt", io.BytesIO(b"abc"))
    assert stored_name == "evil.txt"
    assert bytes_written == 3
    assert (tmp_path / stored_name).read_bytes() == b"abc"


def test_save_stream_enforces_max_upload_bytes_and_cleans_up(tmp_path) -> None:
    svc = FileUploadService(tmp_path, limits=UploadLimits(max_upload_bytes=2))
    with pytest.raises(UploadError):
        svc.save_stream("big.bin", io.BytesIO(b"abc"))
    assert not (tmp_path / "big.bin").exists()

