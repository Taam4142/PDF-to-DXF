"""Generate a small vector PDF for local smoke testing."""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.pdfgen import canvas


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("sample_vector.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output), pagesize=(300, 180))
    c.setTitle("PDF to DXF sample")
    c.setLineWidth(1)
    c.rect(20, 20, 260, 140)
    c.line(40, 50, 250, 50)
    c.line(40, 80, 250, 120)
    path = c.beginPath()
    path.moveTo(60, 130)
    path.curveTo(100, 170, 180, 170, 220, 130)
    c.drawPath(path, stroke=1, fill=0)
    c.setFont("Helvetica", 12)
    c.drawString(40, 145, "VECTOR PDF SAMPLE")
    c.drawString(40, 32, "Converted text")
    c.showPage()

    c.rect(30, 30, 120, 90)
    c.circle(210, 90, 35)
    c.setFont("Helvetica", 10)
    c.drawString(30, 135, "PAGE 2")
    c.save()
    print(output)


if __name__ == "__main__":
    main()
