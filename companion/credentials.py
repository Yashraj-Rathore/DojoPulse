"""Windows per-user DPAPI storage; fail closed on unsupported operating systems."""

import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def crypt(data: bytes, *, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise ValueError("WINDOWS_CREDENTIAL_STORAGE_REQUIRED")
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    library = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    operation = library.CryptUnprotectData if decrypt else library.CryptProtectData
    operation.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    operation.restype = wintypes.BOOL
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ValueError("CREDENTIAL_STORAGE_FAILED")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        if self.path.is_symlink() or self.path.stat().st_size > 2_000_000:
            raise ValueError("INVALID_LOCAL_RECEIPTS")
        result = json.loads(crypt(self.path.read_bytes(), decrypt=True))
        if not isinstance(result, dict):
            raise ValueError("INVALID_LOCAL_RECEIPTS")
        return result

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        if self.path.is_symlink() or temporary.is_symlink():
            raise ValueError("INVALID_LOCAL_RECEIPTS")
        data = json.dumps(state, separators=(",", ":")).encode()
        if len(data) > 1_000_000:
            raise ValueError("LOCAL_RECEIPT_CAPACITY")
        with temporary.open("wb") as stream:
            stream.write(crypt(data))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
