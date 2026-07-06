"""Native Windows desktop app for PDF to DXF conversion."""

from __future__ import annotations

import json
import logging
import math
import os
import queue
import subprocess
import sys
import tempfile
import threading
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import pdfplumber
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from pdf_to_dxf.app_info import (
    APP_DESCRIPTION,
    APP_DIR_NAME,
    APP_DISPLAY_NAME,
    APP_EXECUTABLE_NAME,
    APP_VERSION,
)
from pdf_to_dxf.converter import (
    ConversionOptions,
    ConversionReport,
    convert_pdf_file,
    inspect_pdf_bytes,
    resolve_pages,
)


APP_TITLE = APP_DISPLAY_NAME
MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_SELECTED_PAGES = 50
MAX_ESTIMATED_VECTOR_ENTITIES = 100_000
MAX_ESTIMATED_DXF_ENTITIES = 150_000
MAX_ESTIMATED_CURVE_VERTICES = 500_000
MAX_CURVE_SEGMENTS = 256
WORKER_TIMEOUT_SECONDS = 300
ICON_RESOURCE = Path("assets") / "app_icon.ico"
NO_WARNINGS_TEXT = "No warnings reported."
LOGGER = logging.getLogger("pdf_to_dxf.native")
WorkerResult = tuple[str, dict[str, Any] | None, str | None, str | None]


@dataclass(frozen=True)
class WorkloadEstimate:
    source_name: str
    page_count: int
    selected_pages: list[int]
    selected_page_count: int
    vector_entity_count: int = 0
    text_count: int = 0
    image_count: int = 0
    estimated_dxf_entities: int = 0
    estimated_curve_vertices: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PdfToDxfNativeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("900x680")
        self.minsize(780, 560)
        self._apply_window_icon()

        self.pdf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.pages = tk.StringVar()
        self.unit = tk.StringVar(value="mm")
        self.scale = tk.StringVar(value="1")
        self.curve_segments = tk.StringVar(value="16")
        self.include_text = tk.BooleanVar(value=True)
        self.include_page_border = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready")
        self.metric_vars = {
            "pages": tk.StringVar(value="-"),
            "vectors": tk.StringVar(value="-"),
            "text": tk.StringVar(value="-"),
            "images": tk.StringVar(value="-"),
        }
        self.warning_summary = tk.StringVar(value=NO_WARNINGS_TEXT)
        self.log_path = configure_logging()
        LOGGER.info("Native app started.")

        self.result_queue: queue.Queue[WorkerResult] = queue.Queue()
        self.action_buttons: list[ttk.Button] = []
        self.busy = False

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("MetricValue.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Status.TLabel", foreground="#42526e")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))

    def _apply_window_icon(self) -> None:
        icon_path = resource_path(ICON_RESOURCE)
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError as error:
                LOGGER.warning("Could not apply window icon %s: %s", icon_path, error)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=18)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="About", command=self.show_about).grid(row=0, column=1, sticky="e", padx=(0, 12))
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=2, sticky="e")

        files = ttk.LabelFrame(root, text="Files", padding=12)
        files.grid(row=1, column=0, sticky="ew")
        files.columnconfigure(1, weight=1)
        self._add_file_row(files, 0, "PDF", self.pdf_path, "Select PDF", self.select_pdf)
        self._add_file_row(files, 1, "DXF", self.output_path, "Save As", self.select_output)

        options = ttk.LabelFrame(root, text="Options", padding=12)
        options.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            options.columnconfigure(column, weight=1)

        ttk.Label(options, text="Pages").grid(row=0, column=0, sticky="w")
        ttk.Entry(options, textvariable=self.pages).grid(row=1, column=0, sticky="ew", padx=(0, 12))

        ttk.Label(options, text="Unit").grid(row=0, column=1, sticky="w")
        unit_box = ttk.Combobox(options, textvariable=self.unit, values=("mm", "inch", "pt"), state="readonly")
        unit_box.grid(row=1, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(options, text="Scale").grid(row=0, column=2, sticky="w")
        ttk.Entry(options, textvariable=self.scale).grid(row=1, column=2, sticky="ew", padx=(0, 12))

        ttk.Label(options, text="Curve Segments").grid(row=0, column=3, sticky="w")
        ttk.Entry(options, textvariable=self.curve_segments).grid(row=1, column=3, sticky="ew")

        ttk.Checkbutton(options, text="Text", variable=self.include_text).grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Checkbutton(options, text="Page Border", variable=self.include_page_border).grid(
            row=2, column=1, sticky="w", pady=(12, 0)
        )

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 12))
        actions.columnconfigure(2, weight=1)
        inspect_button = ttk.Button(actions, text="Inspect", command=self.inspect_pdf)
        inspect_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        export_button = ttk.Button(actions, text="Export DXF", command=self.export_dxf, style="Primary.TButton")
        export_button.grid(row=0, column=1, sticky="w")
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=150)
        self.progress.grid(row=0, column=3, sticky="e")
        self.action_buttons.extend([inspect_button, export_button])

        body = ttk.Frame(root)
        body.grid(row=4, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        metrics = ttk.Frame(body)
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            metrics.columnconfigure(column, weight=1)
        self._add_metric(metrics, 0, "Pages", self.metric_vars["pages"])
        self._add_metric(metrics, 1, "Vectors", self.metric_vars["vectors"])
        self._add_metric(metrics, 2, "Text", self.metric_vars["text"])
        self._add_metric(metrics, 3, "Images", self.metric_vars["images"])

        warning_frame = ttk.LabelFrame(body, text="Warnings", padding=8)
        warning_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        warning_frame.columnconfigure(0, weight=1)
        self.warning_label = ttk.Label(
            warning_frame,
            textvariable=self.warning_summary,
            wraplength=760,
            justify="left",
            foreground="#42526e",
        )
        self.warning_label.grid(row=0, column=0, sticky="ew")
        warning_frame.bind(
            "<Configure>",
            lambda event: self.warning_label.configure(wraplength=max(320, event.width - 24)),
        )

        report_frame = ttk.LabelFrame(body, text="Report", padding=8)
        report_frame.grid(row=2, column=0, sticky="nsew")
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)
        self.report_text = scrolledtext.ScrolledText(report_frame, height=14, wrap="none", font=("Consolas", 9))
        self.report_text.grid(row=0, column=0, sticky="nsew")
        self.report_text.configure(state="disabled")

    def _add_file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        button_text: str,
        command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(parent, textvariable=variable, state="readonly").grid(row=row, column=1, sticky="ew", pady=4)
        button = ttk.Button(parent, text=button_text, command=command)
        button.grid(row=row, column=2, sticky="e", padx=(10, 0), pady=4)
        self.action_buttons.append(button)

    def _add_metric(self, parent: ttk.Frame, column: int, label: str, variable: tk.StringVar) -> None:
        box = ttk.Frame(parent, padding=(10, 8), relief="solid")
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        ttk.Label(box, textvariable=variable, style="MetricValue.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(box, text=label).grid(row=1, column=0, sticky="w")

    def select_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
        )
        if not path:
            return
        pdf_path = Path(path)
        self.pdf_path.set(str(pdf_path))
        self.output_path.set(str(pdf_path.with_suffix(".dxf")))
        self.status.set("Ready")
        self._clear_report()

    def select_output(self) -> None:
        initial = self._default_output_path()
        path = filedialog.asksaveasfilename(
            title="Save DXF",
            defaultextension=".dxf",
            initialfile=initial.name,
            initialdir=str(initial.parent),
            filetypes=(("DXF files", "*.dxf"), ("All files", "*.*")),
        )
        if path:
            self.output_path.set(path)

    def show_about(self) -> None:
        messagebox.showinfo(APP_TITLE, build_about_text(self.log_path))

    def inspect_pdf(self) -> None:
        try:
            pdf_path = self._selected_pdf_path()
            options = self._read_options()
        except ValueError as error:
            self._show_validation_error(error)
            return

        def worker() -> dict[str, Any]:
            return inspect_pdf_bytes(pdf_path.read_bytes(), source_name=pdf_path.name, options=options)

        self._run_worker("inspect", "Inspecting PDF...", worker)

    def export_dxf(self) -> None:
        try:
            pdf_path = self._selected_pdf_path()
            output_path = self._selected_output_path()
            if output_path.resolve() == pdf_path.resolve():
                raise ValueError("Choose a DXF output path that is different from the input PDF.")
            options = self._read_options()
        except ValueError as error:
            self._show_validation_error(error)
            return

        if output_path.exists() and not self._confirm_overwrite(output_path):
            self.status.set("Ready")
            return

        def worker() -> dict[str, Any]:
            estimate = estimate_pdf_workload(pdf_path, options)
            validate_workload_estimate(estimate)
            payload = run_conversion_worker(pdf_path, output_path, options)
            payload["_preflight"] = estimate.to_dict()
            payload["_output_path"] = str(output_path)
            return payload

        self._run_worker("convert", "Checking and exporting DXF...", worker)

    def _run_worker(self, kind: str, status: str, worker: Callable[[], dict[str, Any]]) -> None:
        if self.busy:
            return
        self._set_busy(True, status)
        LOGGER.info("Starting %s.", kind)

        def target() -> None:
            try:
                self.result_queue.put((kind, worker(), None, None))
            except ValueError as error:
                self.result_queue.put((kind, None, str(error) or error.__class__.__name__, None))
            except Exception as error:
                self.result_queue.put((kind, None, str(error) or error.__class__.__name__, traceback.format_exc()))

        threading.Thread(target=target, daemon=True).start()
        self.after(100, self._poll_results)

    def _poll_results(self) -> None:
        try:
            kind, payload, error_message, error_detail = self.result_queue.get_nowait()
        except queue.Empty:
            if self.busy:
                self.after(100, self._poll_results)
            return

        self._set_busy(False, "Ready")
        if error_message:
            if error_detail:
                LOGGER.error("%s failed.\n%s", kind, error_detail)
                self._write_report(f"{error_message}\n\nLog file: {self.log_path}\n\n{error_detail}")
                if messagebox.askyesno(APP_TITLE, f"{error_message}\n\nCopy error details to clipboard?"):
                    self.clipboard_clear()
                    self.clipboard_append(error_detail)
            else:
                LOGGER.warning("%s stopped: %s", kind, error_message)
                self._set_warning_summary(error_message, has_warnings=True)
                self._write_report(error_message)
                messagebox.showwarning(APP_TITLE, error_message)
            return

        assert payload is not None
        self._show_report(payload)
        if kind == "convert":
            output_path = payload.get("_output_path", "")
            self.status.set("Exported")
            LOGGER.info("DXF exported to %s.", output_path)
            messagebox.showinfo(APP_TITLE, f"DXF exported:\n{output_path}")
        else:
            self.status.set("Inspected")
            LOGGER.info("PDF inspected.")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        self.status.set(status)
        state = "disabled" if busy else "normal"
        for button in self.action_buttons:
            button.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _show_report(self, report: dict[str, Any]) -> None:
        self.metric_vars["pages"].set(str(report.get("page_count", "-")))
        self.metric_vars["vectors"].set(str(report.get("vector_entity_count", "-")))
        self.metric_vars["text"].set(str(report.get("text_count", "-")))
        self.metric_vars["images"].set(str(report.get("image_count", "-")))
        clean_report = {key: value for key, value in report.items() if not key.startswith("_")}
        has_warnings, warning_summary = build_warning_summary(report)
        self._set_warning_summary(warning_summary, has_warnings=has_warnings)
        self._write_report(json.dumps(clean_report, indent=2, ensure_ascii=False))

    def _clear_report(self) -> None:
        for variable in self.metric_vars.values():
            variable.set("-")
        self._set_warning_summary(NO_WARNINGS_TEXT, has_warnings=False)
        self._write_report("")

    def _set_warning_summary(self, text: str, has_warnings: bool) -> None:
        self.warning_summary.set(text)
        self.warning_label.configure(foreground="#8a4b00" if has_warnings else "#42526e")

    def _write_report(self, text: str) -> None:
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, text)
        self.report_text.configure(state="disabled")

    def _confirm_overwrite(self, output_path: Path) -> bool:
        return messagebox.askyesno(
            APP_TITLE,
            f"{output_path} already exists.\n\nOverwrite this DXF file?",
            icon="warning",
        )

    def _selected_pdf_path(self) -> Path:
        raw = self.pdf_path.get().strip()
        if not raw:
            raise ValueError("Select a PDF file.")
        path = Path(raw)
        if not path.is_file():
            raise ValueError("The selected PDF file does not exist.")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Select a PDF file with a .pdf extension.")
        size = path.stat().st_size
        if size > MAX_PDF_BYTES:
            raise ValueError(
                f"The selected PDF is {format_file_size(size)}. "
                f"The desktop app limit is {format_file_size(MAX_PDF_BYTES)}."
            )
        return path

    def _selected_output_path(self) -> Path:
        raw = self.output_path.get().strip()
        output_path = Path(raw) if raw else self._default_output_path()
        if output_path.suffix.lower() != ".dxf":
            output_path = output_path.with_suffix(".dxf")
        if output_path.exists() and output_path.is_dir():
            raise ValueError("Choose a DXF file path, not a folder.")
        return output_path

    def _default_output_path(self) -> Path:
        raw = self.pdf_path.get().strip()
        if raw:
            return Path(raw).with_suffix(".dxf")
        return Path.home() / "converted.dxf"

    def _read_options(self) -> ConversionOptions:
        return ConversionOptions(
            pages=parse_pages(self.pages.get()),
            unit=self.unit.get(),
            scale=parse_positive_float(self.scale.get(), "Scale"),
            include_text=self.include_text.get(),
            include_page_border=self.include_page_border.get(),
            curve_segments=parse_int_range(self.curve_segments.get(), "Curve Segments", 2, MAX_CURVE_SEGMENTS),
        )

    def _show_validation_error(self, error: ValueError) -> None:
        self.status.set("Ready")
        LOGGER.warning("Validation failed: %s", error)
        self._set_warning_summary(str(error), has_warnings=True)
        messagebox.showwarning(APP_TITLE, str(error))


def configure_logging() -> Path:
    for handler in LOGGER.handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)

    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for log_dir in candidate_log_dirs():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "app.log"
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(formatter)
            LOGGER.addHandler(handler)
            LOGGER.info("Logging initialized at %s.", log_path)
            return log_path
        except OSError:
            continue

    LOGGER.addHandler(logging.NullHandler())
    return Path(tempfile.gettempdir()) / APP_DIR_NAME / "logs" / "app.log"


def resource_path(relative_path: Path) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def build_about_text(log_path: Path) -> str:
    return "\n".join(
        [
            f"{APP_DISPLAY_NAME} {APP_VERSION}",
            APP_DESCRIPTION,
            "",
            f"Executable: {APP_EXECUTABLE_NAME}.exe",
            f"Log file: {log_path}",
            f"Python: {sys.version.split()[0]}",
            f"Tk: {tk.TkVersion}",
            "",
            "This converter works best with vector PDFs exported from CAD, drawing, or layout tools.",
            "Scanned or image-only PDFs are reported but not traced into editable CAD geometry.",
        ]
    )


def candidate_log_dirs() -> list[Path]:
    candidates: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / APP_DIR_NAME / "logs")
    candidates.append(Path(tempfile.gettempdir()) / APP_DIR_NAME / "logs")
    return candidates


def format_file_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} bytes"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.1f} MB"


def estimate_pdf_workload(input_pdf: Path, options: ConversionOptions) -> WorkloadEstimate:
    with pdfplumber.open(str(input_pdf)) as pdf:
        selected_pages = resolve_pages(len(pdf.pages), options.pages)
        estimate = WorkloadEstimate(
            source_name=input_pdf.name,
            page_count=len(pdf.pages),
            selected_pages=selected_pages,
            selected_page_count=len(selected_pages),
        )
        if estimate.selected_page_count > MAX_SELECTED_PAGES:
            return estimate

        vector_entity_count = 0
        text_count = 0
        image_count = 0
        estimated_dxf_entities = 0
        estimated_curve_vertices = 0

        for page_number in selected_pages:
            page = pdf.pages[page_number - 1]
            page_lines = len(page.lines)
            page_rects = len(page.rects)
            page_curves = len(page.curves)
            page_images = len(page.images)
            page_texts = 0
            if options.include_text:
                page_texts = len(page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False))

            page_curve_entities = 0
            page_curve_vertices = 0
            for curve in page.curves:
                curve_entities, curve_vertices = estimate_curve_path_load(
                    curve.get("path", []),
                    options.curve_segments,
                )
                page_curve_entities += curve_entities
                page_curve_vertices += curve_vertices

            vector_entity_count += page_lines + page_rects + page_curves
            text_count += page_texts
            image_count += page_images
            estimated_dxf_entities += page_lines + page_rects + page_curve_entities + page_texts
            if options.include_page_border:
                estimated_dxf_entities += 1
            estimated_curve_vertices += page_curve_vertices

        warnings: list[str] = []
        if image_count and vector_entity_count == 0:
            warnings.append("Raster images are present but no vector geometry was found.")
        elif image_count:
            warnings.append("Raster images will be skipped because raster tracing is not implemented.")

        return WorkloadEstimate(
            source_name=estimate.source_name,
            page_count=estimate.page_count,
            selected_pages=estimate.selected_pages,
            selected_page_count=estimate.selected_page_count,
            vector_entity_count=vector_entity_count,
            text_count=text_count,
            image_count=image_count,
            estimated_dxf_entities=estimated_dxf_entities,
            estimated_curve_vertices=estimated_curve_vertices,
            warnings=warnings,
        )


def estimate_curve_path_load(path: Iterable[tuple[Any, ...]], curve_segments: int) -> tuple[int, int]:
    generated_entities = 0
    generated_vertices = 0
    active_vertices = 0
    has_current_point = False
    has_start_point = False

    def flush() -> None:
        nonlocal active_vertices, generated_entities, generated_vertices
        if active_vertices >= 2:
            generated_entities += 1
            generated_vertices += active_vertices
        active_vertices = 0

    for command in path:
        op = command[0]
        if op == "m":
            flush()
            active_vertices = 1
            has_current_point = True
            has_start_point = True
        elif op == "l" and has_current_point:
            active_vertices += 1
        elif op == "c" and has_current_point:
            active_vertices += max(2, curve_segments)
        elif op == "h":
            if has_current_point and has_start_point:
                active_vertices += 1
            flush()
            has_current_point = has_start_point

    flush()
    return generated_entities, generated_vertices


def validate_workload_estimate(estimate: WorkloadEstimate) -> None:
    errors: list[str] = []
    if estimate.selected_page_count > MAX_SELECTED_PAGES:
        errors.append(
            f"selected pages: {format_count(estimate.selected_page_count)} "
            f"(limit {format_count(MAX_SELECTED_PAGES)})"
        )
    if estimate.vector_entity_count > MAX_ESTIMATED_VECTOR_ENTITIES:
        errors.append(
            f"source vector entities: {format_count(estimate.vector_entity_count)} "
            f"(limit {format_count(MAX_ESTIMATED_VECTOR_ENTITIES)})"
        )
    if estimate.estimated_dxf_entities > MAX_ESTIMATED_DXF_ENTITIES:
        errors.append(
            f"estimated DXF entities: {format_count(estimate.estimated_dxf_entities)} "
            f"(limit {format_count(MAX_ESTIMATED_DXF_ENTITIES)})"
        )
    if estimate.estimated_curve_vertices > MAX_ESTIMATED_CURVE_VERTICES:
        errors.append(
            f"estimated curve vertices: {format_count(estimate.estimated_curve_vertices)} "
            f"(limit {format_count(MAX_ESTIMATED_CURVE_VERTICES)})"
        )

    if errors:
        raise ValueError(build_workload_limit_message(errors, estimate))


def build_workload_limit_message(errors: list[str], estimate: WorkloadEstimate) -> str:
    return "\n".join(
        [
            "This PDF is too large for the desktop app safety limits.",
            "",
            *[f"- {error}" for error in errors],
            "",
            "Preflight estimate:",
            f"- PDF pages: {format_count(estimate.page_count)}",
            f"- Selected pages: {format_count(estimate.selected_page_count)}",
            f"- Source vector entities: {format_count(estimate.vector_entity_count)}",
            f"- Estimated DXF entities: {format_count(estimate.estimated_dxf_entities)}",
            f"- Estimated curve vertices: {format_count(estimate.estimated_curve_vertices)}",
            "",
            "Try selecting fewer pages, lowering curve segments, or splitting the PDF before export.",
        ]
    )


def build_warning_summary(report: dict[str, Any], max_items: int = 5) -> tuple[bool, str]:
    warnings = collect_report_warnings(report)
    if not warnings:
        return False, NO_WARNINGS_TEXT

    visible = warnings[:max_items]
    hidden_count = max(0, len(warnings) - len(visible))
    lines = [f"{format_count(len(warnings))} {pluralize(len(warnings), 'warning')}:"]
    lines.extend(f"- {warning}" for warning in visible)
    if hidden_count:
        lines.append(f"- {format_count(hidden_count)} more {pluralize(hidden_count, 'warning')} in the report.")
    return True, "\n".join(lines)


def collect_report_warnings(report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()

    def append_warning(raw: Any, prefix: str | None = None) -> None:
        text = normalize_warning_text(raw)
        if not text:
            return
        if prefix and f"{prefix}: {text}" in seen:
            return
        if prefix:
            text = f"{prefix}: {text}"
        if text in seen:
            return
        seen.add(text)
        warnings.append(text)

    for warning in iter_warning_values(report.get("warnings")):
        append_warning(warning)

    preflight = report.get("_preflight")
    if isinstance(preflight, dict):
        for warning in iter_warning_values(preflight.get("warnings")):
            append_warning(warning)

    pages = report.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_number = page.get("page_number")
            prefix = f"Page {page_number}" if page_number else None
            for warning in iter_warning_values(page.get("warnings")):
                append_warning(warning, prefix=prefix)

    return warnings


def iter_warning_values(raw: Any) -> Iterable[Any]:
    if isinstance(raw, list):
        yield from raw
    elif isinstance(raw, str):
        yield raw


def normalize_warning_text(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return " ".join(raw.split())


def pluralize(count: int, singular: str) -> str:
    return singular if count == 1 else f"{singular}s"


def format_count(value: int) -> str:
    return f"{value:,}"


def run_conversion_worker(
    input_pdf: Path,
    output_dxf: Path,
    options: ConversionOptions,
    timeout_seconds: int = WORKER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    report_handle = tempfile.NamedTemporaryFile(prefix="pdf-to-dxf-report-", suffix=".json", delete=False)
    report_path = Path(report_handle.name)
    report_handle.close()
    try:
        command = build_worker_command(input_pdf, output_dxf, options, report_path)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            startupinfo=hidden_startupinfo(),
        )
        payload = read_worker_payload(report_path)
        if result.returncode != 0:
            if payload:
                raise RuntimeError(worker_error_message(payload))
            stderr = result.stderr.strip()
            raise RuntimeError(stderr or f"Conversion worker exited with code {result.returncode}.")
        if not payload or not payload.get("ok"):
            raise RuntimeError(worker_error_message(payload or {}))
        report = payload.get("report")
        if not isinstance(report, dict):
            raise RuntimeError("Conversion worker did not return a report.")
        return report
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Conversion timed out after {timeout_seconds} seconds.") from error
    finally:
        report_path.unlink(missing_ok=True)


def build_worker_command(
    input_pdf: Path,
    output_dxf: Path,
    options: ConversionOptions,
    report_path: Path,
) -> list[str]:
    options_json = json.dumps(options_to_payload(options), separators=(",", ":"))
    if getattr(sys, "frozen", False):
        return [
            sys.executable,
            "--worker-convert",
            str(input_pdf),
            str(output_dxf),
            options_json,
            str(report_path),
        ]
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-convert",
        str(input_pdf),
        str(output_dxf),
        options_json,
        str(report_path),
    ]


def hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def read_worker_payload(report_path: Path) -> dict[str, Any] | None:
    if not report_path.is_file() or report_path.stat().st_size == 0:
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def worker_error_message(payload: dict[str, Any]) -> str:
    message = str(payload.get("error") or "Conversion failed.")
    detail = str(payload.get("traceback") or "").strip()
    return f"{message}\n\nWorker detail:\n{detail}" if detail else message


def options_to_payload(options: ConversionOptions) -> dict[str, Any]:
    return {
        "pages": list(options.pages) if options.pages else None,
        "unit": options.unit,
        "scale": options.scale,
        "include_text": options.include_text,
        "include_page_border": options.include_page_border,
        "curve_segments": options.curve_segments,
        "page_gap": options.page_gap,
        "min_line_length": options.min_line_length,
    }


def options_from_payload(payload: dict[str, Any]) -> ConversionOptions:
    pages = payload.get("pages")
    return ConversionOptions(
        pages=tuple(int(page) for page in pages) if pages else None,
        unit=str(payload.get("unit", "mm")),
        scale=float(payload.get("scale", 1.0)),
        include_text=bool(payload.get("include_text", True)),
        include_page_border=bool(payload.get("include_page_border", True)),
        curve_segments=int(payload.get("curve_segments", 16)),
        page_gap=float(payload.get("page_gap", 20.0)),
        min_line_length=float(payload.get("min_line_length", 0.001)),
    )


def run_worker_convert(argv: list[str]) -> int | None:
    if not argv or argv[0] != "--worker-convert":
        return None
    if len(argv) != 5:
        return 2

    report_path = Path(argv[4])
    try:
        options = options_from_payload(json.loads(argv[3]))
        report = convert_pdf_file(Path(argv[1]), Path(argv[2]), options)
        write_worker_payload(report_path, {"ok": True, "report": report.to_dict()})
    except Exception as error:
        write_worker_payload(
            report_path,
            {
                "ok": False,
                "error": str(error) or error.__class__.__name__,
                "traceback": traceback.format_exc(),
            },
        )
        return 1
    return 0


def write_worker_payload(report_path: Path, payload: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_pages(raw: str) -> tuple[int, ...] | None:
    raw = raw.strip()
    if not raw:
        return None
    pages: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            page_number = int(part)
        except ValueError as error:
            raise ValueError("Pages must be comma-separated page numbers.") from error
        if page_number < 1:
            raise ValueError("Pages must be 1 or greater.")
        pages.append(page_number)
    return tuple(pages) or None


def parse_positive_float(raw: str, label: str) -> float:
    try:
        value = float(raw.strip())
    except ValueError as error:
        raise ValueError(f"{label} must be a number.") from error
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")
    if value <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return value


def parse_int_range(raw: str, label: str, minimum: int, maximum: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError as error:
        raise ValueError(f"{label} must be an integer.") from error
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    if value > maximum:
        raise ValueError(f"{label} must be no more than {maximum}.")
    return value


def report_to_dict(report: ConversionReport | dict[str, Any]) -> dict[str, Any]:
    if isinstance(report, ConversionReport):
        return report.to_dict()
    return dict(report)


def run_self_test(argv: list[str]) -> int | None:
    if not argv or argv[0] != "--self-test-convert":
        return None
    if len(argv) != 3:
        return 2
    try:
        convert_pdf_file(Path(argv[1]), Path(argv[2]), ConversionOptions())
    except Exception:
        return 1
    return 0


def main() -> int:
    argv = sys.argv[1:]
    worker_status = run_worker_convert(argv)
    if worker_status is not None:
        return worker_status
    self_test_status = run_self_test(argv)
    if self_test_status is not None:
        return self_test_status
    app = PdfToDxfNativeApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
