"""Shared type aliases for FastAPI dependencies.

This module provides reusable type aliases for common dependency injection patterns
across multiple services, promoting consistency and reducing code duplication.
"""

from typing import Annotated

from fastapi import Depends

from .dependencies import get_current_user

# Cross-service shared dependency types
CurrentUser = Annotated[str, Depends(get_current_user)]
"""Type alias for the current user dependency.

Used across multiple services (BFF, UC, Flow) to inject the authenticated user
via the get_current_user dependency function.
"""