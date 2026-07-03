"""Vector-first PDF to DXF conversion package."""

from .app_info import APP_VERSION
from .converter import ConversionOptions, convert_pdf_bytes, convert_pdf_file, inspect_pdf_bytes

__version__ = APP_VERSION

__all__ = [
    "__version__",
    "ConversionOptions",
    "convert_pdf_bytes",
    "convert_pdf_file",
    "inspect_pdf_bytes",
]
