from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.database import UPLOAD_DIR
from app.models.knowledge import Document, IngestTask
from app.schemas.chat import EmbeddingModel
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


class DocumentIngestService:
    supported_extensions = {".json", ".md", ".txt", ".docx", ".pdf"}
    max_file_size = 20 * 1024 * 1024

    def __init__(self, embedding_service: EmbeddingService, search_service: SearchService) -> None:
        self.embedding_service = embedding_service
        self.search_service = search_service

    async def ingest(
        self,
        db: Session,
        file: UploadFile,
        index_name: str,
        embedding_model: EmbeddingModel,
    ) -> dict:
        filename = self.validate_file(file)
        document_id = uuid.uuid4().hex
        task_id = uuid.uuid4().hex
        saved_path, file_size = self.save_file(file.file, filename, document_id)
        file_hash = self.calculate_file_hash(saved_path)
        duplicate = self.check_duplicate(db, file_hash)
        if duplicate and duplicate.status == "success":
            task = self._create_task(db, task_id, duplicate.id, filename, "success", "duplicate", duplicate.chunk_count)
            return self._response(duplicate, task, status="already_exists", index_name=index_name, embedding_model=embedding_model)

        now = datetime.utcnow()
        document = Document(
            id=document_id,
            filename=filename,
            filepath=str(saved_path),
            file_hash=file_hash,
            file_type=Path(filename).suffix.lower().lstrip("."),
            file_size=file_size,
            chunk_count=0,
            status="pending",
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        task = IngestTask(
            id=task_id,
            document_id=document_id,
            filename=filename,
            status="pending",
            stage="saved",
            error_message=None,
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(document)
        db.add(task)
        db.commit()
        db.refresh(document)
        db.refresh(task)
        return self._response(document, task, index_name=index_name, embedding_model=embedding_model)

    def validate_file(self, file: UploadFile) -> str:
        filename = self._safe_filename(file.filename or "")
        extension = Path(filename).suffix.lower()
        if not filename or extension not in self.supported_extensions:
            supported = ", ".join(sorted(self.supported_extensions))
            raise ValueError(f"Unsupported file type. Supported: {supported}.")
        return filename

    def save_file(self, source: BinaryIO, filename: str, document_id: str) -> tuple[Path, int]:
        target_dir = UPLOAD_DIR / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        size = 0
        with target_path.open("wb") as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_file_size:
                    shutil.rmtree(target_dir, ignore_errors=True)
                    raise ValueError("File too large. Maximum size is 20MB.")
                output.write(chunk)
        if size == 0:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise ValueError("Uploaded file is empty.")
        return target_path, size

    def calculate_file_hash(self, filepath: Path) -> str:
        digest = hashlib.sha256()
        with filepath.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def check_duplicate(self, db: Session, file_hash: str) -> Document | None:
        return db.query(Document).filter(Document.file_hash == file_hash).first()

    def update_document_status(
        self,
        db: Session,
        document: Document,
        status: str,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        document.status = status
        document.error_message = error_message
        document.updated_at = datetime.utcnow()
        if chunk_count is not None:
            document.chunk_count = chunk_count
        db.commit()

    def update_task_status(
        self,
        db: Session,
        task: IngestTask,
        status: str,
        stage: str | None = None,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        task.status = status
        task.stage = stage
        task.error_message = error_message
        task.updated_at = datetime.utcnow()
        if chunk_count is not None:
            task.chunk_count = chunk_count
        db.commit()

    def _create_task(
        self,
        db: Session,
        task_id: str,
        document_id: str,
        filename: str,
        status: str,
        stage: str,
        chunk_count: int,
    ) -> IngestTask:
        now = datetime.utcnow()
        task = IngestTask(
            id=task_id,
            document_id=document_id,
            filename=filename,
            status=status,
            stage=stage,
            error_message=None,
            chunk_count=chunk_count,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def _response(
        self,
        document: Document,
        task: IngestTask,
        status: str | None = None,
        index_name: str | None = None,
        embedding_model: EmbeddingModel | None = None,
    ) -> dict:
        return {
            "document_id": document.id,
            "task_id": task.id,
            "filename": document.filename,
            "file_hash": document.file_hash,
            "chunk_count": document.chunk_count,
            "status": status or document.status,
            "index_name": index_name,
            "embedding_model": embedding_model,
        }

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip().replace("\\", "_").replace("/", "_")
        return re.sub(r"[^A-Za-z0-9._ -]", "_", name)
