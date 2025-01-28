# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pose_to_osc.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['mediapipe', 'python-osc', 'opencv-python'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add mediapipe data files
import mediapipe
mediapipe_path = mediapipe.__path__[0]
a.datas += Tree(mediapipe_path, prefix='mediapipe', excludes=['*.pyc'])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MediaPipe_Body_Tracker',
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
