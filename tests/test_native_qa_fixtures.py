from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pdf_to_dxf import ConversionOptions, inspect_pdf_bytes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_native_qa_fixtures as qa_fixtures  # noqa: E402


class NativeQaFixtureTests(unittest.TestCase):
    def test_generate_fixtures_creates_expected_pdf_behaviors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = qa_fixtures.generate_fixtures(Path(tmpdir))

            self.assertEqual(
                set(manifest),
                {"vector_basic", "raster_with_vector", "raster_only", "multi_page"},
            )
            for path in manifest.values():
                self.assertTrue(path.is_file(), path)
                self.assertGreater(path.stat().st_size, 500, path)

            vector = inspect_pdf_bytes(manifest["vector_basic"].read_bytes(), source_name="vector_basic.pdf")
            mixed = inspect_pdf_bytes(
                manifest["raster_with_vector"].read_bytes(),
                source_name="raster_with_vector.pdf",
            )
            raster = inspect_pdf_bytes(manifest["raster_only"].read_bytes(), source_name="raster_only.pdf")
            multi = inspect_pdf_bytes(
                manifest["multi_page"].read_bytes(),
                source_name="multi_page.pdf",
                options=ConversionOptions(pages=(2,)),
            )

        self.assertEqual(vector["image_count"], 0)
        self.assertGreater(vector["vector_entity_count"], 0)
        self.assertEqual(vector["warnings"], [])

        self.assertGreater(mixed["image_count"], 0)
        self.assertGreater(mixed["vector_entity_count"], 0)
        self.assertTrue(any("raster image" in warning for warning in mixed["warnings"]))

        self.assertGreater(raster["image_count"], 0)
        self.assertEqual(raster["vector_entity_count"], 0)
        self.assertTrue(any("No vector geometry" in warning for warning in raster["warnings"]))
        self.assertTrue(any("Raster images" in warning for warning in raster["warnings"]))

        self.assertEqual(multi["page_count"], 3)
        self.assertEqual(multi["selected_pages"], [2])
        self.assertGreater(multi["vector_entity_count"], 0)


if __name__ == "__main__":
    unittest.main()
