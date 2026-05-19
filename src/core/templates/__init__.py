# src/core/templates/__init__.py

from .models import (
    MachineTemplate,
    Tool,
    LatheOptions
)

from .loader import TemplateLoader

# Nice public API for the rest of the app
__all__ = [
    "MachineTemplate",
    "Tool",
    "LatheOptions",
    "TemplateLoader"
]