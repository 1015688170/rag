from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes.chat import document_ingest_service, search_service
from app.core.database import get_db
from app.schemas.chat import EmbeddingModel
from app.schemas.knowledge import DocumentUploadResponse

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
