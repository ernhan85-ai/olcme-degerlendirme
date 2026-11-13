"""File storage + upload validation + malware scanning hook."""
from __future__ import annotations

import hashlib
import socket
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings

# magic-byte signatures; extension/Content-Type headers are NOT trusted
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
]
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}


class UploadRejected(ValueError):
    def __init__(self, message_tr: str):
        super().__init__(message_tr)
        self.message_tr = message_tr


@dataclass
class ValidatedFile:
    data: bytes
    mime_type: str
    sha256: str
    original_name: str


def sniff_mime(data: bytes) -> str | None:
    for sig, mime in _SIGNATURES:
        if data.startswith(sig):
            return mime
    return None


def validate_upload(data: bytes, filename: str, settings: Settings, allow_json_fixture: bool = False) -> ValidatedFile:
    if not data:
        raise UploadRejected(f"'{filename}' boş bir dosya.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise UploadRejected(f"'{filename}' {settings.max_upload_mb} MB sınırını aşıyor.")
    mime = sniff_mime(data)
    if mime is None and allow_json_fixture and filename.lower().endswith(".transcript.json"):
        mime = "application/json"
    if mime is None:
        raise UploadRejected(f"'{filename}' desteklenmeyen dosya türü. Yalnızca PDF, PNG, JPEG, TIFF yüklenebilir.")
    safe_name = Path(filename).name[:200]
    return ValidatedFile(data, mime, hashlib.sha256(data).hexdigest(), safe_name)


# ---------------------------------------------------------------- malware scan
def scan_for_malware(data: bytes, settings: Settings) -> str:
    """Returns 'clean' | 'infected' | 'not_scanned'. ClamAV via INSTREAM if configured."""
    if settings.malware_scanner != "clamav":
        return "not_scanned"
    with socket.create_connection((settings.clamav_host, settings.clamav_port), timeout=30) as s:
        s.sendall(b"zINSTREAM\0")
        for i in range(0, len(data), 8192):
            chunk = data[i:i + 8192]
            s.sendall(len(chunk).to_bytes(4, "big") + chunk)
        s.sendall(b"\0\0\0\0")
        reply = s.recv(4096).decode(errors="ignore")
    return "infected" if "FOUND" in reply else "clean"


# ---------------------------------------------------------------- storage
class Storage(ABC):
    @abstractmethod
    def put(self, organization_id: uuid.UUID, data: bytes, suffix: str) -> str: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def put(self, organization_id, data, suffix):
        key = f"{organization_id}/{uuid.uuid4().hex}{suffix}"
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def get(self, key):
        return self._path(key).read_bytes()


class S3Storage(Storage):  # pragma: no cover - requires boto3 + bucket
    def __init__(self, settings: Settings):
        raise NotImplementedError(
            "S3 storage: implement with boto3 (put_object with SSE, private ACL, presigned GET). "
            "See docs/INTEGRATIONS.md."
        )

    def put(self, organization_id, data, suffix): ...

    def get(self, key): ...


_MIME_SUFFIX = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg",
                "image/tiff": ".tif", "application/json": ".json"}


def suffix_for(mime: str) -> str:
    return _MIME_SUFFIX.get(mime, ".bin")


def get_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    return LocalStorage(settings.local_storage_dir)
