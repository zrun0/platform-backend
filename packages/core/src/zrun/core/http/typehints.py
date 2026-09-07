"""Shared type-annotation reflection helpers."""

from __future__ import annotations

import types
import typing
from typing import Any

NONE_TYPE = type(None)

# A response model: a Pydantic model class, or `Model | None` for Optional
# contracts where an empty or JSON-null body means "no result".
type ResponseModel[T] = type[T] | types.UnionType | None


def unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Unwrap a `Model | None` annotation.

    Returns the inner type and whether the annotation admits an absent
    (None) value. Non-Optional annotations pass through unchanged.
    """
    origin = typing.get_origin(annotation)
    is_union = origin is typing.Union or origin is types.UnionType
    if is_union and NONE_TYPE in typing.get_args(annotation):
        inner = next(a for a in typing.get_args(annotation) if a is not NONE_TYPE)
        return inner, True
    return annotation, False
