"""Provider failures. Retryability is explicit because a retry is not assumed to be safe."""


class ProviderError(Exception):
    code = "provider_error"
    retryable = False

    def __init__(self, message: str, *, provider: str) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider


class ProviderTimeout(ProviderError):
    code = "timeout"
    retryable = True


class ProviderRateLimited(ProviderError):
    code = "rate_limited"
    retryable = True


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"
    retryable = True


class CircuitOpen(ProviderError):
    code = "circuit_open"
    retryable = False


class UnsafeUrlError(ProviderError):
    code = "unsafe_url"
    retryable = False
