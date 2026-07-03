# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPEC).resolve().parent


a = Analysis(
    ["windows_app.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "pdf_to_dxf" / "static" / "index.html"), "pdf_to_dxf/static")],
    hiddenimports=[
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfdocument",
        "pdfminer.pdfinterp",
        "pdfminer.pdfpage",
        "pdfminer.pdfparser",
        "pdfplumber",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PDF-to-DXF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
