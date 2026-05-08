from __future__ import annotations

import json
from typing import Iterable

VALID_VISIBILITIES = {"public", "private", "department", "role"}


def parse_string_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = text.split(",")
    else:
        parsed = value

    if not isinstance(parsed, list):
        parsed = [parsed]

    items: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def list_to_json(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def validate_document_permissions(
    visibility: str,
    owner_id: str | None,
    allowed_departments: list[str],
    allowed_roles: list[str],
) -> tuple[str, str | None, list[str], list[str]]:
    normalized_visibility = visibility.strip()
    normalized_owner_id = owner_id.strip() if owner_id and owner_id.strip() else None

    if normalized_visibility not in VALID_VISIBILITIES:
        raise ValueError("visibility must be one of: public, private, department, role.")
    if normalized_visibility == "private" and not normalized_owner_id:
        raise ValueError("private documents require owner_id.")
    if normalized_visibility == "department" and not allowed_departments:
        raise ValueError("department documents require allowed_departments.")
    if normalized_visibility == "role" and not allowed_roles:
        raise ValueError("role documents require allowed_roles.")

    return normalized_visibility, normalized_owner_id, allowed_departments, allowed_roles


def document_is_visible(
    *,
    visibility: str,
    owner_id: str | None,
    allowed_departments: str | list[str] | None,
    allowed_roles: str | list[str] | None,
    user_id: str | None,
    department: str | None,
    roles: list[str] | None,
) -> bool:
    if visibility == "public":
        return True
    if user_id and owner_id == user_id:
        return True
    if department and department in parse_string_list(allowed_departments):
        return True
    role_set = set(parse_string_list(roles))
    return bool(role_set and role_set.intersection(parse_string_list(allowed_roles)))
