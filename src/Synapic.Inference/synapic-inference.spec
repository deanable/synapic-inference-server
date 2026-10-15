# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Synapic inference sidecar."""

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
entry = os.path.join(SPECPATH, "service.py")

hiddenimports = [
    "torch", "transformers", "accelerate", "safetensors",
    "huggingface_hub", "tokenizers", "sentencepiece",
    "PIL", "fastapi", "uvicorn", "pydantic", "pydantic_core",
    "anyio", "sniffio", "starlette", "click", "h11",
    "transformers.models.swin2sr",
]
datas = collect_data_files("transformers") + collect_data_files("tokenizers")

a = Analysis(
    [entry], pathex=[SPECPATH], binaries=[], datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "jupyter", "notebook", "pytest",
        "sphinx", "docutils", "cv2", "imagehash", "piexif", "iptcinfo3",
        "faiss", "sentence_transformers", "customtkinter",
    ],
    cipher=block_cipher, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="synapic-inference", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True,
    disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
