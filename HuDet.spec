# HuDet v3.0 - PyInstaller specification
#
# Recommended build:
#     pyinstaller --clean --noconfirm HuDet.spec
#
# This creates:
#     dist/HuDet/HuDet.exe
#
# The application is intentionally built as --onedir. This keeps the
# YOLO/PyTorch runtime manageable and makes assets/configuration easy
# to inspect and update during deployment.

from PyInstaller.utils.hooks import collect_all


# Collect package data and hidden imports needed by the runtime-heavy
# dependencies used by HuDet.
ultralytics_datas, ultralytics_binaries, ultralytics_hiddenimports = collect_all(
    "ultralytics"
)

customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = collect_all(
    "customtkinter"
)

torch_datas, torch_binaries, torch_hiddenimports = collect_all(
    "torch"
)


datas = [
    # Project assets/configuration.
    ("assets", "assets"),
    ("config", "config"),

    # Package data.
    *ultralytics_datas,
    *customtkinter_datas,
    *torch_datas,
]

binaries = [
    *ultralytics_binaries,
    *customtkinter_binaries,
    *torch_binaries,
]

hiddenimports = [
    *ultralytics_hiddenimports,
    *customtkinter_hiddenimports,
    *torch_hiddenimports,

    # Application entry/module imports.
    "model",
    "model.camera_model",
    "model.config_manager",
    "model.counter_model",
    "model.detection_model",
    "model.direction_model",
    "model.plc_model",
    "model.theme_manager",
    "model.tracking_model",
    "view",
    "view.auto_view",
    "view.main_view",
    "view.system_view",
    "view.teach_view",
    "viewmodel",
    "viewmodel.auto_viewmodel",
    "viewmodel.system_viewmodel",
    "viewmodel.teach_viewmodel",
]


a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="HuDet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HuDet",
)
