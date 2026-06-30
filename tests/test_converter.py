from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

from reportlab.pdfgen import canvas

from pdf_to_dxf import ConversionOptions, convert_pdf_bytes, convert_pdf_file, inspect_pdf_bytes
from pdf_to_dxf.dxf_writer import clean_text
from pdf_to_dxf.server import PdfToDxfHandler, options_from_query


class PdfToDxfTests(unittest.TestCase):
    def make_pdf(self, path: Path) -> None:
        c = canvas.Canvas(str(path), pagesize=(200, 100))
        c.line(10, 20, 190, 20)
        c.rect(20, 30, 50, 40)
        bezier = c.beginPath()
        bezier.moveTo(10, 10)
        bezier.curveTo(50, 90, 150, 90, 190, 10)
        c.drawPath(bezier, stroke=1, fill=0)
        c.drawString(30, 80, "PLC01")
        c.showPage()
        c.rect(10, 10, 40, 40)
        c.drawString(20, 70, "PAGE2")
        c.save()

    def test_convert_pdf_bytes_generates_dxf_entities_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            self.make_pdf(pdf_path)

            report, dxf_bytes = convert_pdf_bytes(
                pdf_path.read_bytes(),
                source_name="sample.pdf",
                options=ConversionOptions(pages=(1,), curve_segments=8),
            )
            dxf_text = dxf_bytes.decode("utf-8")

        self.assertIn("SECTION", dxf_text)
        self.assertIn("LINE", dxf_text)
        self.assertIn("POLYLINE", dxf_text)
        self.assertIn("VERTEX", dxf_text)
        self.assertIn("TEXT", dxf_text)
        self.assertIn("PLC01", dxf_text)
        self.assertEqual(report.page_count, 2)
        self.assertEqual(report.selected_pages, [1])
        self.assertGreaterEqual(report.vector_entity_count, 3)
        self.assertGreaterEqual(report.generated_entity_count, 4)

    def test_convert_pdf_file_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            dxf_path = Path(tmpdir) / "sample.dxf"
            self.make_pdf(pdf_path)

            report = convert_pdf_file(pdf_path, dxf_path, ConversionOptions(include_text=False))

            self.assertTrue(dxf_path.exists())
            dxf_text = dxf_path.read_text(encoding="utf-8")

        self.assertIn("EOF", dxf_text)
        self.assertNotIn("PLC01", dxf_text)
        self.assertEqual(report.text_count, 0)

    def test_dxf_text_uses_ascii_replacements(self) -> None:
        dxf_text = clean_text("Temp -40°C >= 1MΩ 50μs")

        self.assertEqual(dxf_text, "Temp -40degC >= 1MOhm 50us")

    def test_inspect_reports_image_free_vector_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            self.make_pdf(pdf_path)

            payload = inspect_pdf_bytes(pdf_path.read_bytes(), source_name="sample.pdf")

        self.assertEqual(payload["source_name"], "sample.pdf")
        self.assertEqual(payload["image_count"], 0)
        self.assertGreater(payload["vector_entity_count"], 0)

    def test_rejects_invalid_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            self.make_pdf(pdf_path)

            with self.assertRaises(ValueError):
                convert_pdf_bytes(pdf_path.read_bytes(), options=ConversionOptions(pages=(3,)))

    def test_query_options_parse_http_parameters(self) -> None:
        options = options_from_query("pages=1,3&unit=inch&scale=2&include_text=false&curve_segments=24")

        self.assertEqual(options.pages, (1, 3))
        self.assertEqual(options.unit, "inch")
        self.assertEqual(options.scale, 2)
        self.assertFalse(options.include_text)
        self.assertEqual(options.curve_segments, 24)

    def test_server_serves_browser_ui(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), PdfToDxfHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                body = response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertIn("<title>PDF to DXF</title>", body)
        self.assertIn("Download DXF", body)


if __name__ == "__main__":
    unittest.main()
