import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes.chat import document_ingest_service, search_service
from app.core.database import get_db
from app.core.permissions import (
    document_is_visible,
    parse_string_list,
    validate_document_permissions,
)
from app.models.knowledge import Document, IngestTask
from app.schemas.chat import EmbeddingModel
from app.schemas.knowledge import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentPermissionUpdateRequest,
    DocumentPermissionUpdateResponse,
    DocumentUploadResponse,
    IngestTaskResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse, summary="Upload a document to an index")
async def upload_document(
    file: UploadFile = File(...),
    index_name: str = Form(...),
    embedding_model: EmbeddingModel = Form(default=EmbeddingModel.ada_002),
    visibility: str = Form("public"),
    owner_id: str | None = Form(None),
    allowed_departments: str = Form("[]"),
    allowed_roles: str = Form("[]"),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    try:
        departments = parse_string_list(allowed_departments)
        roles = parse_string_list(allowed_roles)
        visibility, owner_id, departments, roles = validate_document_permissions(
            visibility,
            owner_id,
            departments,
            roles,
        )
        resolved_index = search_service.resolve_index_name(embedding_model, index_name)
        result = await document_ingest_service.ingest(
            db=db,
            file=file,
            index_name=resolved_index,
            embedding_model=embedding_model,
            visibility=visibility,
            owner_id=owner_id,
            allowed_departments=departments,
            allowed_roles=roles,
        )
        return DocumentUploadResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Document upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed.",
        ) from exc


@router.get("/documents", response_model=DocumentListResponse, summary="List ingested documents")
async def list_documents(
    user_id: str | None = None,
    department: str | None = None,
    roles: str | None = None,
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    role_list = parse_string_list(roles)
    documents = db.query(Document).filter(Document.status != "deleted").order_by(Document.created_at.desc()).all()
    visible_documents = [
        document
        for document in documents
        if document_is_visible(
            visibility=document.visibility,
            owner_id=document.owner_id,
            allowed_departments=document.allowed_departments,
            allowed_roles=document.allowed_roles,
            user_id=user_id,
            department=department,
            roles=role_list,
        )
    ]
    return DocumentListResponse(
        documents=[DocumentListItem.model_validate(doc, from_attributes=True) for doc in visible_documents]
    )


@router.patch(
    "/documents/{document_id}/permissions",
    response_model=DocumentPermissionUpdateResponse,
    summary="Update document permissions",
)
async def update_document_permissions(
    document_id: str,
    request: DocumentPermissionUpdateRequest,
    index_name: str,
    embedding_model: EmbeddingModel = EmbeddingModel.ada_002,
    user_id: str | None = None,
    roles: str | None = None,
    db: Session = Depends(get_db),
) -> DocumentPermissionUpdateResponse:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    role_list = parse_string_list(roles)
    if "admin" not in role_list and (not user_id or document.owner_id != user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this document.")

    try:
        visibility, owner_id, departments, allowed_roles = validate_document_permissions(
            request.visibility,
            request.owner_id,
            request.allowed_departments,
            request.allowed_roles,
        )
        document_ingest_service.update_document_permissions(
            db,
            document,
            visibility,
            owner_id,
            departments,
            allowed_roles,
        )
        resolved_index = search_service.resolve_index_name(embedding_model, index_name)
        updated_chunks = search_service.update_chunk_permissions_by_doc_id(
            resolved_index,
            document.id,
            visibility=document.visibility,
            owner_id=document.owner_id,
            allowed_departments=parse_string_list(document.allowed_departments),
            allowed_roles=parse_string_list(document.allowed_roles),
        )
        return DocumentPermissionUpdateResponse(
            **DocumentListItem.model_validate(document, from_attributes=True).model_dump(),
            updated_chunks=updated_chunks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Document permission update failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document permission update failed.",
        ) from exc


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
    user_id: str | None = None,
    roles: str | None = None,
    db: Session = Depends(get_db),
) -> DocumentDeleteResponse:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.status == "deleted":
        return DocumentDeleteResponse(document_id=document.id, status=document.status, deleted_chunks=0)
    role_list = parse_string_list(roles)
    if "admin" not in role_list and (not user_id or document.owner_id != user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this document.")

    try:
        resolved_index = search_service.resolve_index_name(embedding_model, index_name)
        deleted_chunks = search_service.delete_chunks_by_doc_id(resolved_index, document.id)
        document_ingest_service.update_document_status(db, document, "deleted")
        return DocumentDeleteResponse(document_id=document.id, status="deleted", deleted_chunks=deleted_chunks)
    except Exception as exc:
        logger.exception("Document deletion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document deletion failed.",
        ) from exc
