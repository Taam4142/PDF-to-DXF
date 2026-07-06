from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

import windows_native_app as native
from pdf_to_dxf import ConversionOptions, __version__
from pdf_to_dxf.app_info import APP_EXECUTABLE_NAME, APP_VERSION


class NativeAppHelperTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_native_logger()

    def test_parse_pages_accepts_comma_separated_numbers(self) -> None:
        self.assertEqual(native.parse_pages("1, 3,5"), (1, 3, 5))
        self.assertIsNone(native.parse_pages(""))

    def test_parse_pages_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "comma-separated"):
            native.parse_pages("1,a")
        with self.assertRaisesRegex(ValueError, "1 or greater"):
            native.parse_pages("0")

    def test_numeric_parsers_reject_unbounded_or_unsafe_values(self) -> None:
        self.assertEqual(native.parse_positive_float("1.5", "Scale"), 1.5)
        with self.assertRaisesRegex(ValueError, "finite"):
            native.parse_positive_float("nan", "Scale")
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            native.parse_positive_float("0", "Scale")
        with self.assertRaisesRegex(ValueError, "no more than"):
            native.parse_int_range("999", "Curve Segments", 2, native.MAX_CURVE_SEGMENTS)

    def test_format_file_size(self) -> None:
        self.assertEqual(native.format_file_size(512), "512 bytes")
        self.assertEqual(native.format_file_size(1536), "1.5 KB")
        self.assertEqual(native.format_file_size(2 * 1024 * 1024), "2.0 MB")

    def test_format_count(self) -> None:
        self.assertEqual(native.format_count(1234567), "1,234,567")

    def test_package_version_matches_app_version(self) -> None:
        self.assertEqual(__version__, APP_VERSION)

    def test_icon_asset_exists(self) -> None:
        self.assertTrue((Path.cwd() / native.ICON_RESOURCE).is_file())

    def test_about_text_includes_release_identity_and_diagnostics(self) -> None:
        text = native.build_about_text(Path("C:/logs/app.log"))

        self.assertIn(APP_VERSION, text)
        self.assertIn(APP_EXECUTABLE_NAME, text)
        self.assertIn(f"Log file: {Path('C:/logs/app.log')}", text)
        self.assertIn("Scanned or image-only PDFs", text)

    def test_options_payload_round_trip(self) -> None:
        options = ConversionOptions(pages=(1, 3), unit="inch", scale=2.5, include_text=False, curve_segments=24)

        rebuilt = native.options_from_payload(native.options_to_payload(options))

        self.assertEqual(rebuilt.pages, (1, 3))
        self.assertEqual(rebuilt.unit, "inch")
        self.assertEqual(rebuilt.scale, 2.5)
        self.assertFalse(rebuilt.include_text)
        self.assertEqual(rebuilt.curve_segments, 24)

    def test_estimate_curve_path_load_counts_segment_vertices(self) -> None:
        entities, vertices = native.estimate_curve_path_load(
            [
                ("m", (0, 0)),
                ("c", (10, 0), (20, 0), (30, 0)),
                ("l", (40, 0)),
            ],
            curve_segments=16,
        )

        self.assertEqual(entities, 1)
        self.assertEqual(vertices, 18)

    def test_estimate_pdf_workload_counts_selected_pages_and_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "multi.pdf"
            make_pdf(pdf_path, page_count=2)

            estimate = native.estimate_pdf_workload(
                pdf_path,
                ConversionOptions(pages=(2,), include_text=True, include_page_border=True),
            )

            self.assertEqual(estimate.source_name, "multi.pdf")
            self.assertEqual(estimate.page_count, 2)
            self.assertEqual(estimate.selected_pages, [2])
            self.assertEqual(estimate.selected_page_count, 1)
            self.assertGreaterEqual(estimate.vector_entity_count, 1)
            self.assertGreaterEqual(estimate.text_count, 1)
            self.assertGreaterEqual(estimate.estimated_dxf_entities, estimate.vector_entity_count)

    def test_validate_workload_estimate_rejects_too_many_selected_pages(self) -> None:
        estimate = native.WorkloadEstimate(
            source_name="large.pdf",
            page_count=native.MAX_SELECTED_PAGES + 1,
            selected_pages=list(range(1, native.MAX_SELECTED_PAGES + 2)),
            selected_page_count=native.MAX_SELECTED_PAGES + 1,
        )

        with self.assertRaisesRegex(ValueError, "selected pages"):
            native.validate_workload_estimate(estimate)

    def test_validate_workload_estimate_rejects_too_many_estimated_entities(self) -> None:
        estimate = native.WorkloadEstimate(
            source_name="dense.pdf",
            page_count=1,
            selected_pages=[1],
            selected_page_count=1,
            estimated_dxf_entities=native.MAX_ESTIMATED_DXF_ENTITIES + 1,
        )

        with self.assertRaisesRegex(ValueError, "estimated DXF entities"):
            native.validate_workload_estimate(estimate)

    def test_configure_logging_uses_local_app_data_when_available(self) -> None:
        old_local_app_data = os.environ.get("LOCALAPPDATA")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.environ["LOCALAPPDATA"] = tmpdir
                reset_native_logger()

                log_path = native.configure_logging()
                native.LOGGER.info("test log line")
                for handler in native.LOGGER.handlers:
                    handler.flush()

                self.assertEqual(log_path, Path(tmpdir) / native.APP_DIR_NAME / "logs" / "app.log")
                self.assertIn("test log line", log_path.read_text(encoding="utf-8"))
            finally:
                reset_native_logger()
                if old_local_app_data is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = old_local_app_data

    def test_self_test_conversion_generates_dxf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            dxf_path = Path(tmpdir) / "sample.dxf"
            make_pdf(pdf_path)

            status = native.run_self_test(["--self-test-convert", str(pdf_path), str(dxf_path)])

            self.assertEqual(status, 0)
            self.assertIn("EOF", dxf_path.read_text(encoding="utf-8"))

    def test_conversion_worker_generates_report_and_dxf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            dxf_path = Path(tmpdir) / "sample.dxf"
            make_pdf(pdf_path)

            report = native.run_conversion_worker(pdf_path, dxf_path, ConversionOptions(), timeout_seconds=30)

            self.assertTrue(dxf_path.is_file())
            self.assertIn("EOF", dxf_path.read_text(encoding="utf-8"))
            self.assertEqual(report["source_name"], "sample.pdf")
            self.assertGreater(report["vector_entity_count"], 0)


def make_pdf(path: Path, page_count: int = 1) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(100, 100))
    for page_number in range(1, page_count + 1):
        pdf.line(10, 10, 90, 90)
        pdf.drawString(20, 50, f"NATIVE {page_number}")
        if page_number < page_count:
            pdf.showPage()
    pdf.save()


def reset_native_logger() -> None:
    for handler in list(native.LOGGER.handlers):
        native.LOGGER.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    unittest.main()
