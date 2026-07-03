"""Native Windows desktop app for PDF to DXF conversion."""

from __future__ import annotations

import json
import queue
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from pdf_to_dxf.converter import ConversionOptions, ConversionReport, convert_pdf_file, inspect_pdf_bytes


APP_TITLE = "PDF to DXF"


class PdfToDxfNativeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x680")
        self.minsize(780, 560)

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
        self.result_queue: queue.Queue[tuple[str, dict[str, Any] | None, Exception | None]] = queue.Queue()
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
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").grid(row=0, column=1, sticky="e")

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
        body.rowconfigure(1, weight=1)

        metrics = ttk.Frame(body)
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            metrics.columnconfigure(column, weight=1)
        self._add_metric(metrics, 0, "Pages", self.metric_vars["pages"])
        self._add_metric(metrics, 1, "Vectors", self.metric_vars["vectors"])
        self._add_metric(metrics, 2, "Text", self.metric_vars["text"])
        self._add_metric(metrics, 3, "Images", self.metric_vars["images"])

        report_frame = ttk.LabelFrame(body, text="Report", padding=8)
        report_frame.grid(row=1, column=0, sticky="nsew")
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
            options = self._read_options()
        except ValueError as error:
            self._show_validation_error(error)
            return

        def worker() -> dict[str, Any]:
            report = convert_pdf_file(pdf_path, output_path, options)
            payload = report_to_dict(report)
            payload["_output_path"] = str(output_path)
            return payload

        self._run_worker("convert", "Exporting DXF...", worker)

    def _run_worker(self, kind: str, status: str, worker: Callable[[], dict[str, Any]]) -> None:
        if self.busy:
            return
        self._set_busy(True, status)

        def target() -> None:
            try:
                self.result_queue.put((kind, worker(), None))
            except Exception as error:
                self.result_queue.put((kind, None, error))

        threading.Thread(target=target, daemon=True).start()
        self.after(100, self._poll_results)

    def _poll_results(self) -> None:
        try:
            kind, payload, error = self.result_queue.get_nowait()
        except queue.Empty:
            if self.busy:
                self.after(100, self._poll_results)
            return

        self._set_busy(False, "Ready")
        if error:
            self._write_report(traceback.format_exception_only(type(error), error)[-1].strip())
            messagebox.showerror(APP_TITLE, str(error))
            return

        assert payload is not None
        self._show_report(payload)
        if kind == "convert":
            output_path = payload.get("_output_path", "")
            self.status.set("Exported")
            messagebox.showinfo(APP_TITLE, f"DXF exported:\n{output_path}")
        else:
            self.status.set("Inspected")

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
        self._write_report(json.dumps(clean_report, indent=2, ensure_ascii=False))

    def _clear_report(self) -> None:
        for variable in self.metric_vars.values():
            variable.set("-")
        self._write_report("")

    def _write_report(self, text: str) -> None:
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, text)
        self.report_text.configure(state="disabled")

    def _selected_pdf_path(self) -> Path:
        raw = self.pdf_path.get().strip()
        if not raw:
            raise ValueError("Select a PDF file.")
        path = Path(raw)
        if not path.is_file():
            raise ValueError("The selected PDF file does not exist.")
        return path

    def _selected_output_path(self) -> Path:
        raw = self.output_path.get().strip()
        output_path = Path(raw) if raw else self._default_output_path()
        if output_path.suffix.lower() != ".dxf":
            output_path = output_path.with_suffix(".dxf")
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
            curve_segments=parse_int_at_least(self.curve_segments.get(), "Curve Segments", 2),
        )

    def _show_validation_error(self, error: ValueError) -> None:
        self.status.set("Ready")
        messagebox.showwarning(APP_TITLE, str(error))


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
    if value <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return value


def parse_int_at_least(raw: str, label: str, minimum: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError as error:
        raise ValueError(f"{label} must be an integer.") from error
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
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
    self_test_status = run_self_test(sys.argv[1:])
    if self_test_status is not None:
        return self_test_status
    app = PdfToDxfNativeApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
