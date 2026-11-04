"""Domain errors that do not depend on frameworks or providers."""


class DomainError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AmbiguousAssetError(DomainError):
    code = "ambiguous_asset"


class InvalidAssetError(DomainError):
    code = "invalid_asset"


class InsufficientDataError(DomainError):
    code = "insufficient_data"


class BudgetExceededError(DomainError):
    code = "budget_exceeded"


class DeadlineExceeded(DomainError):
    code = "deadline"


class StructuredOutputError(DomainError):
    code = "invalid_structured_output"
