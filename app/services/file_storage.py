import hashlib
import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_upload(file: FileStorage, upload_dir: Path) -> tuple[Path, str]:
    safe_name = secure_filename(file.filename or "document.pdf")
    target_name = f"{uuid.uuid4().hex}_{safe_name}"
    target_path = upload_dir / target_name
    file.save(target_path)
    return target_path, sha256_file(target_path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
