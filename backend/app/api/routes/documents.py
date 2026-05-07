from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes.chat import document_ingest_service, search_service
from app.core.database import get_db
from app.models.knowledge import Document, IngestTask
from app.schemas.chat import EmbeddingModel
from app.schemas.knowledge import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    IngestTaskResponse,
)

router = APIRouter(tags=["documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse, summary="Upload a document to an index")
async def upload_document(
    file: UploadFile = File(...),
    index_name: str = Form(...),
    embedding_model: EmbeddingModel = Form(default=EmbeddingModel.ada_002),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    try:
        resolved_index = search_service.resolve_index_name(embedding_model, index_name)
        result = await document_ingest_service.ingest(
            db=db,
            file=file,
            index_name=resolved_index,
            embedding_model=embedding_model,
        )
        return DocumentUploadResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {exc}",
        ) from exc


@router.get("/documents", response_model=DocumentListResponse, summary="List ingested documents")
async def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return DocumentListResponse(documents=[DocumentListItem.model_validate(doc, from_attributes=True) for doc in documents])


@router.get("/ingest-tasks/{task_id}", response_model=IngestTaskResponse, summary="Inspect an ingest task")
async def get_ingest_task(task_id: str, db: Session = Depends(get_db)) -> IngestTaskResponse:
    task = db.query(IngestTask).filter(IngestTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingest task not found.")
    return IngestTaskResponse(
        task_id=task.id,
        document_id=task.document_id,
        filename=task.filename,
        status=task.status,
        stage=task.stage,
        chunk_count=task.chunk_count,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse, summary="Delete an ingested document")
async def delete_document(
    document_id: str,
    index_name: str,
    embedding_model: EmbeddingModel = EmbeddingModel.ada_002,
    db: Session = Depends(get_db),
) -> DocumentDeleteResponse:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.status == "deleted":
        return DocumentDeleteResponse(document_id=document.id, status=document.status, deleted_chunks=0)

    try:
        resolved_index = search_service.resolve_index_name(embedding_model, index_name)
        deleted_chunks = search_service.delete_chunks_by_doc_id(resolved_index, document.id)
        document_ingest_service.update_document_status(db, document, "deleted")
        return DocumentDeleteResponse(document_id=document.id, status="deleted", deleted_chunks=deleted_chunks)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {exc}",
        ) from exc
