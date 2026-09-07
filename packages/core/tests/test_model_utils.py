"""Tests for schema-derived partial-update null semantics."""

from __future__ import annotations

from pydantic import BaseModel

from zrun.core.model_utils import partial_update_dict


class StoredProfile(BaseModel):
    """Stored shape: nickname is nullable, name is not."""

    name: str
    nickname: str | None = None


class ProfileUpdate(BaseModel):
    """Request shape: every field optional-to-omit (X | None = None)."""

    name: str | None = None
    nickname: str | None = None


def test_explicit_null_kept_for_nullable_field() -> None:
    """Null on a target-nullable field is kept so it can clear the value."""
    result = partial_update_dict(ProfileUpdate(nickname=None), StoredProfile)

    assert result == {"nickname": None}


def test_explicit_null_dropped_for_required_field() -> None:
    """Null on a target-required field is treated as omitted, even though
    the request-shape annotation admits None (optional-to-omit)."""
    result = partial_update_dict(ProfileUpdate(name=None), StoredProfile)

    assert result == {}


def test_unset_fields_excluded() -> None:
    """Only explicitly-set fields appear in the update dict."""
    result = partial_update_dict(ProfileUpdate(name="new"), StoredProfile)

    assert result == {"name": "new"}


def test_mixed_nulls_resolved_per_target_schema() -> None:
    """A single payload mixes both rules in one pass."""
    result = partial_update_dict(ProfileUpdate(name=None, nickname=None), StoredProfile)

    assert result == {"nickname": None}
