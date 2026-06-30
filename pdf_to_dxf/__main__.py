"""Command line entry points for the PDF to DXF service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .converter import ConversionOptions, convert_pdf_file, inspect_pdf_bytes


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PDF to DXF conversion tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert a vector PDF to DXF.")
    convert_parser.add_argument("input_pdf", type=Path)
    convert_parser.add_argument("output_dxf", type=Path)
    add_conversion_options(convert_parser)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect conversion quality without keeping a DXF.")
    inspect_parser.add_argument("input_pdf", type=Path)
    add_conversion_options(inspect_parser)

    serve_parser = subparsers.add_parser("serve", help="Run the local HTTP API.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", default=8765, type=int)

    args = parser.parse_args(argv)
    if args.command == "convert":
        report = convert_pdf_file(args.input_pdf, args.output_dxf, build_options(args))
        print(report.to_json())
        return
    if args.command == "inspect":
        payload = inspect_pdf_bytes(args.input_pdf.read_bytes(), source_name=args.input_pdf.name, options=build_options(args))
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if args.command == "serve":
        from .server import main as server_main

        server_main(["--host", args.host, "--port", str(args.port)])
        return

    parser.error(f"Unknown command: {args.command}")


def add_conversion_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pages", help="Comma-separated 1-based page numbers, for example: 1,3")
    parser.add_argument("--unit", choices=["mm", "inch", "pt"], default="mm")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--no-text", action="store_true", help="Skip PDF text extraction.")
    parser.add_argument("--no-page-border", action="store_true", help="Skip page outline geometry.")
    parser.add_argument("--curve-segments", type=int, default=16)
    parser.add_argument("--page-gap", type=float, default=20.0)


def build_options(args: argparse.Namespace) -> ConversionOptions:
    return ConversionOptions(
        pages=parse_pages(args.pages),
        unit=args.unit,
        scale=args.scale,
        include_text=not args.no_text,
        include_page_border=not args.no_page_border,
        curve_segments=args.curve_segments,
        page_gap=args.page_gap,
    )


def parse_pages(raw: str | None) -> tuple[int, ...] | None:
    if not raw:
        return None
    pages = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    return pages or None


if __name__ == "__main__":
    main(sys.argv[1:])
