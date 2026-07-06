"""Generate PDF fixtures for native Windows app manual QA."""

from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


DEFAULT_OUTPUT_DIR = Path("out/native-qa")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate native app QA PDFs.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true", help="Print the fixture manifest as JSON.")
    args = parser.parse_args(argv)

    manifest = generate_fixtures(args.output_dir)
    if args.json:
        print(json.dumps({key: str(path) for key, path in manifest.items()}, indent=2))
    else:
        for label, path in manifest.items():
            print(f"{label}: {path}")
    return 0


def generate_fixtures(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "vector_basic": output_dir / "vector_basic.pdf",
        "raster_with_vector": output_dir / "raster_with_vector.pdf",
        "raster_only": output_dir / "raster_only.pdf",
        "multi_page": output_dir / "multi_page.pdf",
    }
    make_vector_basic(manifest["vector_basic"])
    make_raster_with_vector(manifest["raster_with_vector"])
    make_raster_only(manifest["raster_only"])
    make_multi_page(manifest["multi_page"])
    return manifest


def make_vector_basic(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(320, 220))
    pdf.setTitle("Native QA Vector Basic")
    pdf.setLineWidth(1.2)
    pdf.rect(24, 24, 272, 172)
    pdf.line(44, 58, 276, 58)
    pdf.line(44, 86, 276, 146)
    curve = pdf.beginPath()
    curve.moveTo(52, 160)
    curve.curveTo(94, 205, 226, 205, 268, 160)
    pdf.drawPath(curve, stroke=1, fill=0)
    pdf.drawString(44, 178, "NATIVE QA VECTOR")
    pdf.drawString(44, 38, "Expected: vectors, text, no images, no warnings")
    pdf.save()


def make_raster_with_vector(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(320, 220))
    pdf.setTitle("Native QA Raster With Vector")
    draw_test_image(pdf, "RASTER + VECTOR", 42, 58, 236, 116)
    pdf.setLineWidth(1.0)
    pdf.rect(34, 48, 252, 136)
    pdf.line(42, 38, 278, 38)
    pdf.drawString(42, 190, "Expected: image warning, vector export still works")
    pdf.save()


def make_raster_only(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(320, 220))
    pdf.setTitle("Native QA Raster Only")
    draw_test_image(pdf, "RASTER ONLY", 38, 42, 244, 136)
    pdf.save()


def make_multi_page(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(260, 180))
    pdf.setTitle("Native QA Multi Page")
    for page_number in range(1, 4):
        pdf.setLineWidth(1.0)
        pdf.rect(24, 24, 212, 132)
        pdf.line(42, 54, 218, 54 + (page_number * 18))
        pdf.drawString(42, 136, f"NATIVE QA PAGE {page_number}")
        pdf.drawString(42, 36, "Use Pages = 2 to confirm selected page export.")
        if page_number < 3:
            pdf.showPage()
    pdf.save()


def draw_test_image(pdf: canvas.Canvas, label: str, x: float, y: float, width: float, height: float) -> None:
    image = make_test_image(label)
    pdf.drawImage(ImageReader(image), x, y, width=width, height=height, preserveAspectRatio=False)


def make_test_image(label: str) -> BytesIO:
    image = Image.new("RGB", (360, 180), "#f5f7fb")
    draw = ImageDraw.Draw(image)
    for x in range(0, 360, 24):
        color = "#d6e4ff" if (x // 24) % 2 == 0 else "#fce8c8"
        draw.rectangle((x, 0, x + 24, 180), fill=color)
    draw.rectangle((18, 18, 342, 162), outline="#0f5132", width=5)
    draw.line((36, 132, 324, 48), fill="#842029", width=5)
    draw.text((42, 78), label, fill="#111827")

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
