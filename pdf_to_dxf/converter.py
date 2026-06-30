"""PDF vector extraction and DXF conversion."""

from __future__ import annotations

import json
import math
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pdfplumber

from .dxf_writer import DxfWriter


POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4


@dataclass(frozen=True)
class ConversionOptions:
    pages: tuple[int, ...] | None = None
    unit: str = "mm"
    scale: float = 1.0
    include_text: bool = True
    include_page_border: bool = True
    curve_segments: int = 16
    page_gap: float = 20.0
    min_line_length: float = 0.001


@dataclass
class PageReport:
    page_number: int
    width: float
    height: float
    lines: int = 0
    rects: int = 0
    curves: int = 0
    texts: int = 0
    images: int = 0
    generated_entities: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ConversionReport:
    source_name: str
    page_count: int
    selected_pages: list[int]
    unit: str
    scale: float
    vector_entity_count: int = 0
    text_count: int = 0
    image_count: int = 0
    generated_entity_count: int = 0
    pages: list[PageReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def convert_pdf_file(input_pdf: Path, output_dxf: Path, options: ConversionOptions | None = None) -> ConversionReport:
    report, dxf_bytes = convert_pdf_bytes(input_pdf.read_bytes(), source_name=input_pdf.name, options=options)
    output_dxf.parent.mkdir(parents=True, exist_ok=True)
    output_dxf.write_bytes(dxf_bytes)
    return report


def convert_pdf_bytes(
    raw: bytes,
    source_name: str = "uploaded.pdf",
    options: ConversionOptions | None = None,
) -> tuple[ConversionReport, bytes]:
    if not raw:
        raise ValueError("PDF body is empty.")
    opts = options or ConversionOptions()
    validate_options(opts)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)

    try:
        with pdfplumber.open(str(tmp_path)) as pdf:
            selected_pages = resolve_pages(len(pdf.pages), opts.pages)
            writer = DxfWriter(unit=opts.unit)
            report = ConversionReport(
                source_name=source_name,
                page_count=len(pdf.pages),
                selected_pages=selected_pages,
                unit=opts.unit,
                scale=opts.scale,
            )

            x_offset = 0.0
            for index, page_number in enumerate(selected_pages):
                page = pdf.pages[page_number - 1]
                page_report = convert_page(page, writer, opts, page_number, x_offset)
                report.pages.append(page_report)
                report.vector_entity_count += page_report.lines + page_report.rects + page_report.curves
                report.text_count += page_report.texts
                report.image_count += page_report.images
                report.generated_entity_count += page_report.generated_entities
                report.warnings.extend(f"Page {page_number}: {warning}" for warning in page_report.warnings)

                page_width = convert_length(page.width, opts)
                if index < len(selected_pages) - 1:
                    x_offset += page_width + opts.page_gap

            if report.vector_entity_count == 0:
                report.warnings.append("No vector geometry was found. The PDF may be scanned or image-only.")
            if report.image_count and report.vector_entity_count == 0:
                report.warnings.append("Raster images are present but raster tracing is not implemented.")

            return report, writer.to_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def inspect_pdf_bytes(raw: bytes, source_name: str = "uploaded.pdf", options: ConversionOptions | None = None) -> dict[str, Any]:
    report, _ = convert_pdf_bytes(raw, source_name=source_name, options=options)
    return report.to_dict()


def convert_page(
    page: Any,
    writer: DxfWriter,
    options: ConversionOptions,
    page_number: int,
    x_offset: float,
) -> PageReport:
    page_width = convert_length(page.width, options)
    page_height = convert_length(page.height, options)
    page_report = PageReport(
        page_number=page_number,
        width=page_width,
        height=page_height,
        lines=len(page.lines),
        rects=len(page.rects),
        curves=len(page.curves),
        images=len(page.images),
    )
    before_count = len(writer.entities)

    if options.include_page_border:
        writer.add_lwpolyline(
            [
                (x_offset, 0),
                (x_offset + page_width, 0),
                (x_offset + page_width, page_height),
                (x_offset, page_height),
            ],
            layer="PDF_PAGE",
            closed=True,
            color=8,
        )

    for line in page.lines:
        start = convert_pdf_point(line["x0"], line["y0"], page.height, options, x_offset=x_offset, y_is_top=False)
        end = convert_pdf_point(line["x1"], line["y1"], page.height, options, x_offset=x_offset, y_is_top=False)
        if distance(start, end) >= options.min_line_length:
            writer.add_line(start, end, layer="PDF_LINES")

    for rect in page.rects:
        x0, y0 = convert_pdf_point(rect["x0"], rect["y0"], page.height, options, x_offset=x_offset, y_is_top=False)
        x1, y1 = convert_pdf_point(rect["x1"], rect["y1"], page.height, options, x_offset=x_offset, y_is_top=False)
        writer.add_lwpolyline(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
            layer="PDF_RECTS",
            closed=True,
        )

    for curve in page.curves:
        add_curve_paths(writer, curve.get("path", []), page.height, options, x_offset)

    if options.include_text:
        words = page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False)
        page_report.texts = len(words)
        for word in words:
            text = str(word.get("text", ""))
            x = float(word.get("x0", 0))
            bottom = float(word.get("bottom", page.height))
            top = float(word.get("top", bottom))
            height = max(convert_length(bottom - top, options), convert_length(2, options))
            insert = convert_pdf_point(x, bottom, page.height, options, x_offset=x_offset, y_is_top=True)
            writer.add_text(text, insert, height, layer="PDF_TEXT", color=2)

    if page.images:
        page_report.warnings.append(
            f"{len(page.images)} raster image(s) were skipped; vector geometry still exports."
        )

    page_report.generated_entities = len(writer.entities) - before_count
    return page_report


def add_curve_paths(
    writer: DxfWriter,
    path: Iterable[tuple[Any, ...]],
    page_height: float,
    options: ConversionOptions,
    x_offset: float,
) -> None:
    points: list[tuple[float, float]] = []
    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None

    def flush(closed: bool = False) -> None:
        nonlocal points
        if len(points) >= 2:
            writer.add_lwpolyline(deduplicate_points(points), layer="PDF_CURVES", closed=closed)
        points = []

    for command in path:
        op = command[0]
        if op == "m":
            flush()
            current = convert_path_point(command[1], page_height, options, x_offset)
            start = current
            points = [current]
        elif op == "l" and current is not None:
            current = convert_path_point(command[1], page_height, options, x_offset)
            points.append(current)
        elif op == "c" and current is not None:
            p0 = current
            p1 = convert_path_point(command[1], page_height, options, x_offset)
            p2 = convert_path_point(command[2], page_height, options, x_offset)
            p3 = convert_path_point(command[3], page_height, options, x_offset)
            for step in range(1, max(2, options.curve_segments) + 1):
                t = step / max(2, options.curve_segments)
                points.append(cubic_bezier(p0, p1, p2, p3, t))
            current = p3
        elif op == "h":
            if start is not None and current is not None and distance(current, start) > options.min_line_length:
                points.append(start)
            flush(closed=True)
            current = start
    flush()


def validate_options(options: ConversionOptions) -> None:
    if options.unit not in {"mm", "inch", "pt"}:
        raise ValueError("unit must be one of: mm, inch, pt.")
    if not math.isfinite(options.scale) or options.scale <= 0:
        raise ValueError("scale must be a positive number.")
    if options.curve_segments < 2:
        raise ValueError("curve_segments must be at least 2.")
    if options.page_gap < 0:
        raise ValueError("page_gap must be zero or greater.")
    if options.pages is not None and not options.pages:
        raise ValueError("pages cannot be empty.")


def resolve_pages(page_count: int, requested: tuple[int, ...] | None) -> list[int]:
    if page_count <= 0:
        raise ValueError("PDF has no pages.")
    if requested is None:
        return list(range(1, page_count + 1))
    pages: list[int] = []
    for page in requested:
        if page < 1 or page > page_count:
            raise ValueError(f"Page {page} is outside the PDF page range 1-{page_count}.")
        if page not in pages:
            pages.append(page)
    return pages


def convert_length(value: float, options: ConversionOptions) -> float:
    if options.unit == "mm":
        unit_factor = MM_PER_INCH / POINTS_PER_INCH
    elif options.unit == "inch":
        unit_factor = 1.0 / POINTS_PER_INCH
    else:
        unit_factor = 1.0
    return float(value) * unit_factor * options.scale


def convert_pdf_point(
    x: float,
    y: float,
    page_height: float,
    options: ConversionOptions,
    x_offset: float,
    y_is_top: bool,
) -> tuple[float, float]:
    cad_x = x_offset + convert_length(float(x), options)
    pdf_y = page_height - float(y) if y_is_top else float(y)
    cad_y = convert_length(pdf_y, options)
    return cad_x, cad_y


def convert_path_point(
    point: tuple[float, float],
    page_height: float,
    options: ConversionOptions,
    x_offset: float,
) -> tuple[float, float]:
    return convert_pdf_point(point[0], point[1], page_height, options, x_offset=x_offset, y_is_top=True)


def cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return x, y


def distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.hypot(end[0] - start[0], end[1] - start[1])


def deduplicate_points(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    clean: list[tuple[float, float]] = []
    for point in points:
        if not clean or distance(clean[-1], point) > 1e-9:
            clean.append(point)
    return clean
