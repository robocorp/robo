from pathlib import Path
import platform
from typing import Literal

from playwright.sync_api import Browser, sync_playwright as _sync_playwright


def _registry_path(browser: Literal["chrome", "firefox"]) -> str:
    if platform.system() == "Windows":
        import winreg

        location = winreg.HKEY_LOCAL_MACHINE
        browser_registry = (
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{browser}.exe"
        )
        key = winreg.OpenKeyEx(location, browser_registry)
        # empty string key gets the (Default) value
        path = winreg.QueryValueEx(key, "")
        assert path, f"Could not find {browser} path"
        return path
    raise RuntimeError("Not implemented for this OS")


EXECUTABLE_PATHS = {
    "chromium": {
        "Linux": "/usr/bin/chromium-browser",
        "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    },
    "firefox": {
        "Linux": "/usr/bin/firefox",
        "Windows": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        "Darwin": "/Applications/Firefox.app/Contents/MacOS/firefox",
    },
}


def _get_executable_path(browser: Literal["firefox", "chrome"]) -> str:
    system = platform.system()
    if system == "Windows":
        return _registry_path(browser)

    system = platform.system()
    assert browser in EXECUTABLE_PATHS
    executable_path = EXECUTABLE_PATHS[browser][system]
    assert Path(executable_path).exists()
    return executable_path


def open_available_browser(
    browser: Literal["firefox", "chrome"] = "chrome",
    headless=True
    # TODO: support more args
) -> Browser:
    playwright = _sync_playwright().start()

    assert playwright
    # TODO: allow user to also pass their own custom path?
    executable_path = _get_executable_path(browser)

    launched_browser = playwright[browser].launch(
        executable_path=executable_path, headless=headless
    )
    return launched_browser


#     Open Available Browser    http://rpachallenge.com/


# Close All Browsers


#  Click Button    Start


# Input Text    alias:First Name    ${person}[First Name]


# Capture Element Screenshot    alias:Congratulations
