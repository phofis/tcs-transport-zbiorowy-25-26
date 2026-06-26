from __future__ import annotations

from app.models import Stop


def format_stop_display_name(stop: Stop) -> str:
    if stop.platform:
        return f"{stop.name} {stop.platform}"
    return stop.name
