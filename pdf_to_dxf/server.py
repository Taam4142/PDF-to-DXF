"""Local HTTP API for PDF to DXF conversion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .converter import ConversionOptions, convert_pdf_bytes, inspect_pdf_bytes


MAX_BODY_BYTES = 50 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the local PDF to DXF API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), PdfToDxfHandler)
    print(f"PDF to DXF API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


class PdfToDxfHandler(BaseHTTPRequestHandler):
    server_version = "PdfToDxf/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            self.send_static_html("index.html")
            return
        if parsed.path == "/health":
            self.send_json({"ok": True, "service": "pdf-to-dxf"})
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/convert", "/convert/pdf-to-dxf"}:
            self.handle_convert(parsed.query)
            return
        if parsed.path == "/inspect":
            self.handle_inspect(parsed.query)
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def handle_convert(self, query: str) -> None:
        try:
            raw = self.read_raw_body()
            source_name = self.headers.get("X-File-Name", "uploaded.pdf")
            options = options_from_query(query)
            report, dxf_bytes = convert_pdf_bytes(raw, source_name=source_name, options=options)
        except Exception as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_response(HTTPStatus.OK)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/dxf")
        self.send_header("Content-Disposition", 'attachment; filename="converted.dxf"')
        self.send_header("Content-Length", str(len(dxf_bytes)))
        self.send_header("X-Vector-Entities", str(report.vector_entity_count))
        self.send_header("X-Text-Count", str(report.text_count))
        self.send_header("X-Image-Count", str(report.image_count))
        self.end_headers()
        self.wfile.write(dxf_bytes)

    def handle_inspect(self, query: str) -> None:
        try:
            raw = self.read_raw_body()
            source_name = self.headers.get("X-File-Name", "uploaded.pdf")
            payload = inspect_pdf_bytes(raw, source_name=source_name, options=options_from_query(query))
        except Exception as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_json(payload)

    def read_raw_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is empty.")
        if content_length > MAX_BODY_BYTES:
            raise ValueError("Request body is too large.")
        return self.rfile.read(content_length)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static_html(self, name: str) -> None:
        path = STATIC_DIR / name
        if not path.is_file():
            self.send_json({"error": "UI asset not found"}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-File-Name")

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def options_from_query(query: str) -> ConversionOptions:
    params = parse_qs(query, keep_blank_values=False)
    return ConversionOptions(
        pages=parse_pages(first(params, "pages") or first(params, "page")),
        unit=first(params, "unit", "mm"),
        scale=parse_float(first(params, "scale", "1"), "scale"),
        include_text=parse_bool(first(params, "include_text", "true")),
        include_page_border=parse_bool(first(params, "include_page_border", "true")),
        curve_segments=parse_int(first(params, "curve_segments", "16"), "curve_segments"),
        page_gap=parse_float(first(params, "page_gap", "20"), "page_gap"),
    )


def first(params: dict[str, list[str]], key: str, default: str = "") -> str:
    values = params.get(key)
    return values[0] if values else default


def parse_pages(raw: str) -> tuple[int, ...] | None:
    if not raw:
        return None
    pages = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    return pages or None


def parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def parse_float(raw: str, name: str) -> float:
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number.") from error


def parse_int(raw: str, name: str) -> int:
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


if __name__ == "__main__":
    main()
