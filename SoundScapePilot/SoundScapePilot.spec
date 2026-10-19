# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# pydantic_core ships a native .pyd extension; collect_all gets binaries + datas + hiddenimports
pydantic_core_datas, pydantic_core_binaries, pydantic_core_hidden = collect_all('pydantic_core')

webview_datas, webview_binaries, webview_hidden = collect_all('webview')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=webview_binaries + pydantic_core_binaries,
    datas=[('static', 'static'), ('web', 'web'), ('modules', 'modules')] + webview_datas + pydantic_core_datas,
    hiddenimports=[
        'webview',
        'webview.platforms.edgechromium',
    ] + webview_hidden + pydantic_core_hidden + [
        # engine modules (namespace package: no __init__.py, so be explicit)
        'modules.ai_marketing',
        'modules.booking_agent',
        'modules.catalog_manager',
        'modules.database',
        'modules.distribution_pipeline',
        'modules.epk_engine',
        'modules.label_identity',
        'modules.mailer',
        'modules.pr_wire',
        'modules.pricing_model',
        'modules.radio_finder',
        'modules.royalty_engine',
        'modules.sync_licensing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_pydantic.py'],
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
    name='SoundScapePilot',
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
    icon='logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SoundScapePilot',
)
