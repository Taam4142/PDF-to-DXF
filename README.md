# PDF to DXF Service

Standalone Python service for converting vector PDF drawings into DXF files.

This is intentionally a vector-first converter. It works best with PDFs exported
from CAD, drawing, or layout tools. Scanned PDFs and image-only PDFs are reported
as raster-heavy and are not traced in this first version.

## What It Includes

- CLI converter: PDF file in, DXF file out.
- Local HTTP API with `/health`, `/inspect`, and `/convert/pdf-to-dxf`.
- Local browser UI served at `/`.
- Native Windows desktop app with file picker, inspect, and export controls.
- Lightweight DXF writer with no CAD dependency required.
- PDF vector extraction using `pdfplumber`.
- Multi-page support with horizontal page offsets.
- Conversion report with page counts, vector counts, text counts, image counts,
  and warnings.
- Test suite that generates a vector PDF fixture with `reportlab`.

## Planning Docs

- [Project working process](docs/project-working-process.md)
- [Native app risk and quality plan](docs/native-app-risk-quality-plan.md)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you use the bundled Codex Python runtime, replace `.\.venv\Scripts\python.exe`
with that Python path.

## CLI Usage

Convert a PDF:

```powershell
.\.venv\Scripts\python.exe -m pdf_to_dxf convert input.pdf output.dxf
```

Convert only page 1:

```powershell
.\.venv\Scripts\python.exe -m pdf_to_dxf convert input.pdf output.dxf --pages 1
```

Inspect a PDF without writing DXF:

```powershell
.\.venv\Scripts\python.exe -m pdf_to_dxf inspect input.pdf
```

Run the local HTTP service:

```powershell
.\.venv\Scripts\python.exe -m pdf_to_dxf serve --host 127.0.0.1 --port 8765
```

Or use the launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Then open:

```text
http://127.0.0.1:8765/
```

## Native Windows Desktop App

The project includes a native Windows desktop launcher. It opens as a normal
Windows app with file picker, conversion options, inspect, and DXF export
controls. It does not start a browser or depend on the local HTTP server.
Exports run in a separate worker process, write DXF files atomically, and ask
before replacing an existing `.dxf` file. App logs are written under
`%LOCALAPPDATA%\PDF-to-DXF\logs\app.log`, with a temp-folder fallback if that
location is unavailable. The desktop build includes an app icon, Windows file
version metadata, and an About dialog with version and diagnostics details.

Build the executable:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe .\windows_native_app.spec --noconfirm --clean --distpath dist\windows-native-app --workpath build\pyinstaller-native
```

Run the built app:

```powershell
.\dist\windows-native-app\PDF-to-DXF-Desktop.exe
```

For automated smoke tests:

```powershell
.\dist\windows-native-app\PDF-to-DXF-Desktop.exe --self-test-convert .\examples\sample_vector.pdf .\examples\sample_from_desktop.dxf
```

Build the Windows installer after the executable has been built:

```powershell
choco install innosetup -y
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_installer.ps1
```

The installer is written to:

```text
dist\installer\PDF-to-DXF-Desktop-Setup-0.1.0.exe
```

GitHub Actions also builds and smoke-tests the Windows desktop executable on
every push to `main`, then packages it into an Inno Setup installer. Download
the `PDF-to-DXF-Desktop-installer-windows` artifact from the **Windows Desktop
Build** workflow run for normal installation, or `PDF-to-DXF-Desktop-windows`
when you specifically want the raw executable.

The browser-based Windows launcher is still available through
`windows_app.spec` when you specifically want the local web UI packaged as an
`.exe`.

Run with Docker:

```powershell
docker build -t pdf-to-dxf-service .
docker run --rm -p 8765:8765 pdf-to-dxf-service
```

## Deploy To Vercel

This repository includes a Vercel-compatible WSGI adapter:

- `api/index.py`
- `app.py`
- `pdf_to_dxf/vercel_app.py`
- `vercel.json`

Deploy from GitHub:

1. Push this repository to GitHub.
2. In Vercel, choose **Add New Project**.
3. Import the GitHub repository.
4. Keep the default build settings.
5. Deploy.

Deploy with the Vercel CLI:

```powershell
npm install -g vercel
vercel
```

The deployed app serves the same paths as local development:

- `/`
- `/health`
- `/inspect`
- `/convert/pdf-to-dxf`

Vercel serverless deployments have request size and execution time limits. For
large scanned PDFs, batch conversion, or long-running raster tracing, prefer the
Docker image on a container host.

## HTTP API

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

Inspect a PDF:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/inspect `
  -Method Post `
  -InFile .\drawing.pdf `
  -ContentType application/pdf `
  -Headers @{ "X-File-Name" = "drawing.pdf" }
```

Convert a PDF:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8765/convert/pdf-to-dxf?pages=1&unit=mm&scale=1" `
  -Method Post `
  -InFile .\drawing.pdf `
  -ContentType application/pdf `
  -Headers @{ "X-File-Name" = "drawing.pdf" } `
  -OutFile .\drawing.dxf
```

The same request is available as a script:

```powershell
powershell -ExecutionPolicy Bypass -File examples\convert_api.ps1 .\drawing.pdf .\drawing.dxf
```

## Query Options

- `pages`: comma-separated 1-based page numbers, for example `1,3`.
- `unit`: `mm`, `inch`, or `pt`. Default is `mm`.
- `scale`: multiplier applied after unit conversion. Default is `1`.
- `include_text`: `true` or `false`. Default is `true`.
- `include_page_border`: `true` or `false`. Default is `true`.
- `curve_segments`: number of segments per Bezier curve. Default is `16`.
- `page_gap`: gap between pages in output units. Default is `20`.

## Important Limits

PDF is not CAD. A PDF usually does not preserve layers, blocks, constraints,
true CAD object names, or exact manufacturing intent. This service converts
visible vector geometry into CAD-readable DXF geometry.

Raster images are counted and reported, but not traced. If `image_count` is high
and `vector_entity_count` is zero, the PDF is probably scanned or image-only.

For production CAD workflows, review the generated DXF in your CAD tool and keep
the original PDF attached for traceability.

## Development

Generate a sample vector PDF:

```powershell
.\.venv\Scripts\python.exe examples\make_sample_pdf.py examples\sample_vector.pdf
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Or run the PowerShell smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File tests\smoke.ps1
```
