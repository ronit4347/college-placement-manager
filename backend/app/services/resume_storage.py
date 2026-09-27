import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_SIZE = 64 * 1024


def get_resume_directory() -> Path:
    directory = settings.resume_upload_dir
    if not directory.is_absolute():
        project_root = Path(__file__).resolve().parents[3]
        directory = project_root / directory
    resolved = directory.resolve()
    if resolved.is_dir():
        os.chmod(resolved, 0o700)
        for stored_file in resolved.iterdir():
            if not stored_file.is_symlink() and stored_file.is_file():
                os.chmod(stored_file, 0o600)
    return resolved


async def save_resume_upload(upload: UploadFile) -> str:
    if not upload.filename or Path(upload.filename).suffix.lower() != ".pdf":
        await upload.close()
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Resume must be a PDF file.")
    if upload.content_type != "application/pdf":
        await upload.close()
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Resume must be uploaded as application/pdf.")

    directory = get_resume_directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    filename = f"{uuid4().hex}.pdf"
    temporary_path = directory / f".{filename}.upload"
    final_path = directory / filename
    total_size = 0
    signature = bytearray()

    try:
        descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            while chunk := await upload.read(UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > settings.max_resume_size_bytes:
                    max_size_mib = settings.max_resume_size_bytes / (1024 * 1024)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Resume must not exceed {max_size_mib:.1f} MiB.",
                    )
                if len(signature) < len(PDF_SIGNATURE):
                    signature.extend(chunk[: len(PDF_SIGNATURE) - len(signature)])
                destination.write(chunk)
        if bytes(signature) != PDF_SIGNATURE:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Uploaded file is not a valid PDF.")
        os.replace(temporary_path, final_path)
        return filename
    finally:
        await upload.close()
        temporary_path.unlink(missing_ok=True)


def remove_resume(filename: str | None) -> None:
    if filename:
        (get_resume_directory() / Path(filename).name).unlink(missing_ok=True)


def resume_path(filename: str | None) -> Path | None:
    if not filename or Path(filename).name != filename:
        return None
    path = get_resume_directory() / filename
    if not path.is_file():
        return None
    os.chmod(path, 0o600)
    return path
