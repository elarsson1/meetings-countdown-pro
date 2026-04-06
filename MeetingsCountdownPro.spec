# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Meetings Countdown Pro."""

import os
import sys
from pathlib import Path

# Import version from the package so there's a single source of truth
sys.path.insert(0, SPECPATH)
from meetings_countdown_pro import __version__

block_cipher = None

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # In-package SVG assets (menu bar icon, clapperboard, etc.)
        (str(ROOT / "meetings_countdown_pro" / "assets"), "meetings_countdown_pro/assets"),
    ],
    hiddenimports=[
        # pyobjc frameworks used at runtime
        "objc",
        "EventKit",
        "Foundation",
        # PyQt6 plugins that PyInstaller sometimes misses
        "PyQt6.QtSvg",
        "PyQt6.QtMultimedia",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused Qt modules to reduce bundle size
        "PyQt6.QtWebEngine",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtDesigner",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MeetingsCountdownPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI app, no terminal window
    target_arch=None,       # Build for current architecture
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MeetingsCountdownPro",
)

app = BUNDLE(
    coll,
    name="Meetings Countdown Pro.app",
    icon=str(ROOT / "assets" / "AppIcon.icns"),
    bundle_identifier="com.axeltech.meetings-countdown-pro",
    version=__version__,
    info_plist={
        "CFBundleName": "Meetings Countdown Pro",
        "CFBundleDisplayName": "Meetings Countdown Pro",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": True,            # Menu-bar app — no Dock icon
        "NSCalendarsUsageDescription":
            "Meetings Countdown Pro needs calendar access to show "
            "upcoming meetings and start countdowns before they begin.",
        "NSCalendarsFullAccessUsageDescription":
            "Meetings Countdown Pro needs calendar access to show "
            "upcoming meetings and start countdowns before they begin.",
        "NSMicrophoneUsageDescription":
            "This app does not use the microphone.",
        "NSHighResolutionCapable": True,
    },
)
