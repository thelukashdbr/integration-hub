class DomainError(Exception):
    """Base for errors raised by services. Translated to HTTP responses in main.py,
    so services never depend on FastAPI."""


class NotFoundError(DomainError):
    def __init__(self, resource: str, resource_id: object) -> None:
        super().__init__(f"{resource} {resource_id} not found")


class ConflictError(DomainError):
    """The request is valid but the current state doesn't allow it (HTTP 409)."""
