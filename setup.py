import shutil

from setuptools import setup

MACMON = shutil.which("macmon") or "/opt/homebrew/bin/macmon"

setup(
    name="wptemps",
    app=["wptemps_app.py"],
    options={"py2app": {
        "argv_emulation": False,
        "iconfile": "wptemps.icns",
        "plist": {
            "LSUIElement": True,
            "CFBundleName": "wptemps",
            "CFBundleDisplayName": "wptemps",
            "CFBundleIdentifier": "com.wptemps.app",
            "CFBundleShortVersionString": "1.0.0",
            "NSHumanReadableCopyright": "wptemps — voir THIRD_PARTY_NOTICES.md",
        },
        "packages": ["wptemps"],
        # import lazy dans login.py -> py2app ne le decouvre pas seul
        "includes": ["ServiceManagement"],
        "resources": [MACMON, "THIRD_PARTY_NOTICES.md"],
    }},
    setup_requires=["py2app"],
)
