from __future__ import annotations

import hashlib
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from fastapi import UploadFile

from app.schemas.chat import EmbeddingModel
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


class DocumentIngestService:
    supported_extensions = {".json", ".md", ".txt", ".docx", ".pdf"}

    def __init__(self, embedding_service: EmbeddingService, search_service: SearchService) -> None:
        self.embedding_service = embedding_service
        self.search_service = search_service

    async def ingest(
        self,
        file: UploadFile,
        index_name: str,
        embedding_model: EmbeddingModel,
    ) -> dict[str, Any]:
        raw = await file.read()
        filename = Path(file.filename or "uploaded-document").name
        text = self._extract_text(filename, raw)
        chunks = self._chunk_text(text)
        documents = [
            {
                "id": self._chunk_id(filename, index),
                "filepath": filename,
                "content": chunk,
                "content_vector": self.embedding_service.embed(chunk, embedding_model),
            }
            for index, chunk in enumerate(chunks)
        ]
        uploaded_count = self.search_service.upload_documents(index_name=index_name, documents=documents)
        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "uploaded_count": uploaded_count,
        }

    def _extract_text(self, filename: str, raw: bytes) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in self.supported_extensions:
            supported = ", ".join(sorted(self.supported_extensions))
            raise ValueError(f"Unsupported file type: {extension or 'unknown'}. Supported: {supported}.")
        if extension == ".json":
            return self._extract_json(raw)
        if extension in {".md", ".txt"}:
            return raw.decode("utf-8-sig")
        if extension == ".docx":
            return self._extract_docx(raw)
        if extension == ".pdf":
            return self._extract_pdf(raw)
        raise ValueError(f"Unsupported file type: {extension}.")

    def _extract_json(self, raw: bytes) -> str:
        data = json.loads(raw.decode("utf-8-sig"))
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _extract_docx(self, raw: bytes) -> str:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
            if text.strip():
                paragraphs.append(text)
        return "\n".join(paragraphs)

    def _extract_pdf(self, raw: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF upload requires the pypdf package.") from exc

        reader = PdfReader(BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _chunk_text(self, text: str, chunk_size: int = 1200, overlap: int = 160) -> list[str]:
        normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not normalized:
            raise ValueError("Uploaded document has no extractable text.")

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(normalized):
                break
            start = max(end - overlap, start + 1)
        return chunks

    def _chunk_id(self, filename: str, index: int) -> str:
        digest = hashlib.sha1(f"{filename}:{index}".encode("utf-8")).hexdigest()
        return f"upload-{digest}"
