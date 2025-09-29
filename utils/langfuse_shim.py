# utils/langfuse_shim.py
from __future__ import annotations
from typing import Optional, Any

# ── No-op implementacje (działa zawsze) ──────────────────────────────────────
class _NoOpObservation:
    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    # pozwala używać "with langfuse.trace(...):"
    def __enter__(self) -> "_NoOpObservation":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        pass

    def update(self, **kwargs: Any) -> None:
        # bezpieczny no-op
        pass

    @property
    def id(self) -> None:
        return None


class _NoOpLangfuse:
    """Zastępuje klienta Langfuse, jeśli nieobecny lub niekompletny."""
    def trace(self, **kwargs: Any) -> _NoOpObservation:
        return _NoOpObservation(**kwargs)

    def span(self, **kwargs: Any) -> _NoOpObservation:
        return _NoOpObservation(**kwargs)

    def event(self, **kwargs: Any) -> _NoOpObservation:
        return _NoOpObservation(**kwargs)

    def generation(self, **kwargs: Any) -> _NoOpObservation:
        return _NoOpObservation(**kwargs)


class _DummyCtx:
    """Shim na API kontekstu Langfuse, żeby nie wywalało się na update_*."""
    @staticmethod
    def update_current_observation(**kwargs: Any) -> None:
        pass

    @staticmethod
    def update_current_trace(**kwargs: Any) -> None:
        pass

    @staticmethod
    def update_current_span(**kwargs: Any) -> None:
        pass


# Domyślne (działają zawsze)
langfuse: Any = _NoOpLangfuse()
langfuse_context: Any = _DummyCtx()

def observe(name: Optional[str] = None):
    """Dekorator zgodny interfejsem – no-op gdy brak pakietu/nowego API."""
    def _decorator(func):
        return func
    return _decorator


# ── Próby podmiany na prawdziwe API, jeśli dostępne ─────────────────────────
try:
    # Najpierw sprawdźmy, czy mamy nowy moduł dekoratorów (>=2.22.0)
    try:
        from langfuse.decorators import observe as _obs, langfuse_context as _ctx  # type: ignore
        observe = _obs          # type: ignore[assignment]
        langfuse_context = _ctx # type: ignore[assignment]
    except Exception:
        # zostajemy przy no-opach dla dekoratorów/kontekstu
        pass

    # Teraz spróbuj zainicjalizować klienta i zobaczyć, czy ma .trace()
    try:
        from langfuse import Langfuse as _Langfuse  # type: ignore
        _client = _Langfuse()
        # Jeżeli klient ma metody trace/span/event/generation – używamy prawdziwego
        if all(hasattr(_client, m) for m in ("trace", "span", "event")):
            langfuse = _client  # type: ignore[assignment]
        # W niektórych wersjach mogą istnieć inne nazwy/metody – wówczas zachowaj no-op
    except Exception:
        pass

except Exception:
    # Całkowity fallback – zostają no-opy zadeklarowane powyżej
    pass
