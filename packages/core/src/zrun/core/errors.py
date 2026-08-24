"""Base error types shared across zrun services."""


class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(self, message: str = "Application error") -> None:
        super().__init__(message)
        self.message = message


class ServiceCallError(AppError):
    """Raised when a downstream service call fails.

    Attributes:
        service_name: Name of the downstream service.
        status_code: HTTP status code from the downstream response, if any.
        response_body: Raw response body from the downstream, if any.
    """

    def __init__(
        self,
        message: str = "Service call failed",
        *,
        service_name: str = "unknown",
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.service_name = service_name
        self.status_code = status_code
        self.response_body = response_body


class ServiceTimeoutError(ServiceCallError):
    """Raised when a downstream service call times out."""

    def __init__(
        self,
        message: str = "Service call timed out",
        *,
        service_name: str = "unknown",
    ) -> None:
        super().__init__(message, service_name=service_name, status_code=504)


class ServiceUnavailableError(ServiceCallError):
    """Raised when a downstream service cannot be reached."""

    def __init__(
        self,
        message: str = "Service unavailable",
        *,
        service_name: str = "unknown",
    ) -> None:
        super().__init__(message, service_name=service_name, status_code=502)


class ServiceBadRequestError(ServiceCallError):
    """Raised when a downstream service returns a 4xx response."""


class ServiceNotFoundError(ServiceBadRequestError):
    """Raised when a downstream service returns a 404 response."""

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        service_name: str = "unknown",
        response_body: str | None = None,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=404,
            response_body=response_body,
        )
