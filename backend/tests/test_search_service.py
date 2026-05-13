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
