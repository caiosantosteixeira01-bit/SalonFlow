# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path(SPECPATH)
package_dir = project_dir / "salao"
main_script = project_dir / "main.py"
version_ns = {}
exec((package_dir / "core" / "version.py").read_text(encoding="utf-8"), version_ns)
app_name = version_ns["APP_NAME"]
app_version = version_ns["APP_VERSION"]
icon_path = package_dir / "assets" / "SalonFlow.ico"

datas = [
    (str(package_dir / "assets"), "salao/assets"),
]
datas += collect_data_files("reportlab")
datas += collect_data_files("pypdf")

hiddenimports = []
hiddenimports += collect_submodules("reportlab")
hiddenimports += collect_submodules("pypdf")

a = Analysis(
    [str(main_script)],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

