from __future__ import annotations

import hashlib
import math
import os
import uuid

from fastapi import HTTPException, status

from app.core.config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()

    def _upload_dir(self, upload_id: str) -> str:
        return os.path.join(self.settings.upload_tmp_dir, upload_id)

    def init_multipart(
        self,
        *,
        user_id: uuid.UUID,
        file_name: str,
        file_size: int,
        mime_type: str | None,
        folder_id: str | None,
    ) -> dict:
        if file_size > self.settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"code": "ERR_FILE_TOO_LARGE", "message": "文件过大", "details": {"max": self.settings.max_upload_bytes}},
            )
        upload_id = str(uuid.uuid4())
        chunk_size = int(self.settings.upload_chunk_size)
        total_chunks = int(math.ceil(file_size / chunk_size))

        upload_dir = self._upload_dir(upload_id)
        os.makedirs(upload_dir, exist_ok=True)

        meta = {
            "upload_id": upload_id,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "folder_id": folder_id,
            "user_id": str(user_id),
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
        }
        with open(os.path.join(upload_dir, "meta.json"), "w", encoding="utf-8") as f:
            import json

            json.dump(meta, f, ensure_ascii=False)

        return {"upload_id": upload_id, "chunk_size": chunk_size, "total_chunks": total_chunks}

    def save_chunk(self, *, upload_id: str, user_id: uuid.UUID, chunk_index: int, body: bytes) -> None:
        upload_dir = self._upload_dir(upload_id)
        if not os.path.isdir(upload_dir):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_UPLOAD_NOT_FOUND", "message": "upload_id 不存在", "details": {}},
            )
        meta = self._load_meta(upload_id)
        if meta.get("user_id") != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_UPLOAD_NOT_FOUND", "message": "upload_id 不存在", "details": {}},
            )
        if chunk_index < 0 or chunk_index >= int(meta["total_chunks"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR_INVALID_CHUNK", "message": "分片序号无效", "details": {"chunk_index": chunk_index}},
            )
        if len(body) > self.settings.upload_chunk_size + 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"code": "ERR_CHUNK_TOO_LARGE", "message": "分片过大", "details": {}},
            )
        part_path = os.path.join(upload_dir, f"{chunk_index}.part")
        with open(part_path, "wb") as f:
            f.write(body)

    def _load_meta(self, upload_id: str) -> dict:
        upload_dir = self._upload_dir(upload_id)
        meta_path = os.path.join(upload_dir, "meta.json")
        if not os.path.isfile(meta_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_UPLOAD_NOT_FOUND", "message": "upload_id 不存在", "details": {}},
            )
        import json

        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def complete_multipart(self, *, upload_id: str, user_id: uuid.UUID) -> dict:
        meta = self._load_meta(upload_id)
        if meta.get("user_id") != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ERR_UPLOAD_NOT_FOUND", "message": "upload_id 不存在", "details": {}},
            )
        upload_dir = self._upload_dir(upload_id)

        total_chunks = int(meta["total_chunks"])
        parts: list[str] = []
        for i in range(total_chunks):
            part_path = os.path.join(upload_dir, f"{i}.part")
            if not os.path.isfile(part_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "ERR_MISSING_CHUNK", "message": "分片缺失", "details": {"chunk_index": i}},
                )
            parts.append(part_path)

        final_rel = os.path.join(str(user_id), str(uuid.uuid4()), meta["file_name"])
        final_path = os.path.join(self.settings.storage_dir, final_rel)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        sha256 = hashlib.sha256()
        total_written = 0
        with open(final_path, "wb") as out:
            for part in parts:
                with open(part, "rb") as f:
                    while True:
                        buf = f.read(1024 * 1024)
                        if not buf:
                            break
                        sha256.update(buf)
                        out.write(buf)
                        total_written += len(buf)

        if total_written != int(meta["file_size"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ERR_SIZE_MISMATCH",
                    "message": "文件大小校验失败",
                    "details": {"expected": meta["file_size"], "actual": total_written},
                },
            )

        return {
            "file_path": final_rel.replace("\\", "/"),
            "file_size": total_written,
            "sha256": sha256.hexdigest(),
            "mime_type": meta.get("mime_type"),
            "original_name": meta.get("file_name"),
            "folder_id": meta.get("folder_id"),
        }

    def save_direct_upload(self, *, user_id: uuid.UUID, filename: str, body: bytes) -> dict:
        if len(body) > self.settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"code": "ERR_FILE_TOO_LARGE", "message": "文件过大", "details": {"max": self.settings.max_upload_bytes}},
            )
        final_rel = os.path.join(str(user_id), str(uuid.uuid4()), filename)
        final_path = os.path.join(self.settings.storage_dir, final_rel)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        sha256 = hashlib.sha256(body).hexdigest()
        with open(final_path, "wb") as f:
            f.write(body)

        return {
            "file_path": final_rel.replace("\\", "/"),
            "file_size": len(body),
            "sha256": sha256,
        }
