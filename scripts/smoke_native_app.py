from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from reportlab.pdfgen import canvas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test the packaged native Windows app.")
    parser.add_argument("--exe", required=True, type=Path, help="Path to PDF-to-DXF-Desktop.exe")
    parser.add_argument("--work-dir", default=Path("out/native-smoke"), type=Path)
    args = parser.parse_args(argv)

    exe_path = args.exe.resolve()
    work_dir = args.work_dir.resolve()
    if not exe_path.is_file():
        raise FileNotFoundError(f"Executable not found: {exe_path}")

    work_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = work_dir / "smoke_vector.pdf"
    dxf_path = work_dir / "smoke_vector.dxf"
    report_path = work_dir / "worker_report.json"

    make_pdf(pdf_path)
    options = {
        "pages": None,
        "unit": "mm",
        "scale": 1,
        "include_text": True,
        "include_page_border": True,
        "curve_segments": 16,
        "page_gap": 20,
        "min_line_length": 0.001,
    }

    result = subprocess.run(
        [
            str(exe_path),
            "--worker-convert",
            str(pdf_path),
            str(dxf_path),
            json.dumps(options, separators=(",", ":")),
            str(report_path),
        ],
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Worker exited with code {result.returncode}.")
    if not report_path.is_file():
        raise RuntimeError("Worker did not write a report file.")
    if not dxf_path.is_file():
        raise RuntimeError("Worker did not write a DXF file.")

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(f"Worker reported failure: {payload!r}")
    report = payload.get("report") or {}
    if report.get("vector_entity_count", 0) <= 0:
        raise RuntimeError(f"Expected vector entities in report: {report!r}")

    dxf_text = dxf_path.read_text(encoding="utf-8")
    if "AC1009" not in dxf_text or not dxf_text.rstrip().endswith("EOF"):
        raise RuntimeError("DXF output does not look valid.")

    print(
        json.dumps(
            {
                "exe": str(exe_path),
                "dxf": str(dxf_path),
                "vector_entity_count": report["vector_entity_count"],
                "generated_entity_count": report["generated_entity_count"],
            },
            indent=2,
        )
    )
    return 0


def make_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=(200, 120))
    pdf.line(10, 20, 190, 20)
    pdf.rect(30, 35, 70, 45)
    curve = pdf.beginPath()
    curve.moveTo(20, 80)
    curve.curveTo(60, 115, 140, 115, 180, 80)
    pdf.drawPath(curve, stroke=1, fill=0)
    pdf.drawString(45, 95, "SMOKE")
    pdf.save()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
