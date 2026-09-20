"""Request-scoped context (currently just the correlation ID)."""
from contextvars import ContextVar

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id_ctx.set(correlation_id)
