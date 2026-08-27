# zrun-test-utils

Shared test utilities and fixtures for zrun platform backend.

## Usage

```python
from zrun_test_utils.helpers import ok_response, error_response


def test_api_client():
    # Create successful response
    response = ok_response({"user": "alice"})

    # Create error response
    error = error_response("User not found", status=404)
```

## Installation

This package is part of the zrun workspace and should be available to all workspace members automatically.
