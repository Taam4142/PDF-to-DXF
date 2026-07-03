from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

import windows_native_app as native
from pdf_to_dxf import ConversionOptions


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

    def test_options_payload_round_trip(self) -> None:
        options = ConversionOptions(pages=(1, 3), unit="inch", scale=2.5, include_text=False, curve_segments=24)

        rebuilt = native.options_from_payload(native.options_to_payload(options))

        self.assertEqual(rebuilt.pages, (1, 3))
        self.assertEqual(rebuilt.unit, "inch")
        self.assertEqual(rebuilt.scale, 2.5)
        self.assertFalse(rebuilt.include_text)
        self.assertEqual(rebuilt.curve_segments, 24)

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


def make_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(100, 100))
    pdf.line(10, 10, 90, 90)
    pdf.drawString(20, 50, "NATIVE")
    pdf.save()


def reset_native_logger() -> None:
    for handler in list(native.LOGGER.handlers):
        native.LOGGER.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    unittest.main()
