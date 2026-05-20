"""Render launchd plist templates with {{PLACEHOLDER}} substitution."""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def render_launchd_plist(template: str, values: dict[str, str]) -> str:
    unknown = set(_PLACEHOLDER_RE.findall(template)) - set(values)
    if unknown:
        msg = f"unknown placeholders: {sorted(unknown)}"
        raise ValueError(msg)
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    leftover = set(_PLACEHOLDER_RE.findall(rendered))
    if leftover:
        msg = f"unsubstituted placeholders: {sorted(leftover)}"
        raise ValueError(msg)
    return rendered


def load_rendered_plist(rendered: str) -> dict:
    return plistlib.loads(rendered.encode("utf-8"))


def render_plist_file(template_path: Path, values: dict[str, str]) -> dict:
    template = template_path.read_text()
    rendered = render_launchd_plist(template, values)
    return load_rendered_plist(rendered)
