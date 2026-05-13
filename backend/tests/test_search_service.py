from __future__ import annotations

from types import SimpleNamespace

from app.services.search_service import SearchService


def test_permission_filter_defaults_to_public_only() -> None:
    service = SearchService(SimpleNamespace())

    assert service._permission_filter() == "visibility eq 'public'"


def test_permission_filter_escapes_and_deduplicates_identity_fields() -> None:
    service = SearchService(SimpleNamespace())

    result = service._permission_filter(
        user_id="alice'o",
        department="sre'east",
        roles=["admin", "admin", "on'call", " "],
    )

    assert result == (
        "visibility eq 'public' or "
        "owner_id eq 'alice''o' or "
        "allowed_departments/any(d: d eq 'sre''east') or "
        "allowed_roles/any(r: search.in(r, 'admin,on''call'))"
    )


def test_search_row_to_document_keeps_chunk_and_source_doc_ids_distinct() -> None:
    service = SearchService(SimpleNamespace())

    result = service._search_row_to_document(
        {
            "id": "chunk-key-1",
            "doc_id": "parent-doc-1",
            "chunk_id": "chunk-1",
            "filepath": "runbook.md",
            "content": "rollback steps",
            "section_title": "Rollback",
            "source_type": "md",
            "page_start": 2,
            "page_end": 3,
            "@search.score": 4.5,
        }
    )

    assert result["doc_id"] == "chunk-key-1"
    assert result["source_doc_id"] == "parent-doc-1"
    assert result["chunk_id"] == "chunk-1"
    assert result["section_title"] == "Rollback"
    assert result["source_type"] == "md"
    assert result["page_start"] == 2
    assert result["page_end"] == 3
    assert result["recall_score"] == 4.5
