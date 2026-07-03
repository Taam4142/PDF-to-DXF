# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPEC).resolve().parent
sys.path.insert(0, str(ROOT))

from pdf_to_dxf.app_info import (
    APP_COMPANY,
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_EXECUTABLE_NAME,
    APP_PRODUCT_NAME,
    APP_VERSION,
)


ICON_PATH = ROOT / "assets" / "app_icon.ico"


def version_tuple(value):
    parts = [int(part) for part in value.split(".")]
    return tuple((parts + [0, 0, 0, 0])[:4])


VERSION = version_tuple(APP_VERSION)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=VERSION,
        prodvers=VERSION,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", APP_COMPANY),
                        StringStruct("FileDescription", APP_DESCRIPTION),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", APP_EXECUTABLE_NAME),
                        StringStruct("LegalCopyright", APP_COPYRIGHT),
                        StringStruct("OriginalFilename", f"{APP_EXECUTABLE_NAME}.exe"),
                        StringStruct("ProductName", APP_PRODUCT_NAME),
                        StringStruct("ProductVersion", APP_VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)


a = Analysis(
    ["windows_native_app.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ICON_PATH), "assets")],
    hiddenimports=[
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfdocument",
        "pdfminer.pdfinterp",
        "pdfminer.pdfpage",
        "pdfminer.pdfparser",
        "pdfplumber",
        "PIL.Image",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
        "tkinter.ttk",
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
    name=APP_EXECUTABLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=str(ICON_PATH),
    version=VERSION_INFO,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
