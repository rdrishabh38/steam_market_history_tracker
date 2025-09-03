# -*- mode: python ; coding: utf-8 -*-

import customtkinter
import os

# Get the path to the customtkinter library automatically
customtkinter_path = os.path.dirname(customtkinter.__file__)

block_cipher = None

a = Analysis(['app.py'],
             pathex=[],
             binaries=[],
             datas=[
                 (customtkinter_path, 'customtkinter')
             ],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='SteamMarketHistoryTracker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_dir=None,
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
