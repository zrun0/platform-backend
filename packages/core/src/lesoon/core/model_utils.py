"""Shared Pydantic helpers for partial-update (PUT/PATCH) semantics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from lesoon.core.http.typehints import unwrap_optional


def partial_update_dict(payload: BaseModel, target: type[BaseModel]) -> dict[str, Any]:
    """Dump explicitly-set fields with schema-derived null semantics.

    A field explicitly set to None is kept when the field is nullable in
    the ``target`` (stored) model — the null clears the stored value — and
    dropped otherwise (required fields treat null as "omitted").

    Nullability is deliberately derived from the target model, not from
    the payload model: request shapes use ``X | None = None`` to mean
    "field may be omitted", which says nothing about whether the stored
    value may be null. Deriving from the schema keeps the contract correct
    as fields are added, instead of hand-maintained per-service lists.

    Callers overlay the result with ``model_copy(update=...)``, which skips
    re-validation — the payload was already validated at parse time.
    """
    target_nullable = {
        name for name, field in target.model_fields.items() if unwrap_optional(field.annotation)[1]
    }
    return {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or key in target_nullable
    }
