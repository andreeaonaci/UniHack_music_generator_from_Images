"""Global settings for the app.

Provides a simple process-global view flag so any module can query whether
we're in the Timisoara view or the Romania view.
"""
from threading import Lock

_lock = Lock()
_view = "ro"  # 'ro' for Romania, 'tm' for Timisoara


def set_view(view: str) -> None:
    """Set the current view. Accepts 'ro' or 'tm'."""
    global _view
    with _lock:
        if view not in ("ro", "tm"):
            raise ValueError("view must be 'ro' or 'tm'")
        _view = view


def get_view() -> str:
    """Return the current view string ('ro' or 'tm')."""
    with _lock:
        return _view


def is_timisoara() -> bool:
    """Convenience helper that returns True when current view is Timisoara."""
    return get_view() == "tm"
