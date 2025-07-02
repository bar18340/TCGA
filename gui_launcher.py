"""
TCGA Data Merger Tool - Desktop GUI Launcher

This script launches the TCGA web application in a native desktop window using PyWebView.
It starts the Flask server on a free port (prefers 5000), waits for it to become available,
and then opens a Chromium-powered window pointing to the web interface.

Key Features:
- Automatically finds a free port for the Flask server.
- Launches Flask in a background thread to keep the UI responsive.
- Waits for the server to be ready before opening the window.
- Uses PyWebView to provide a native desktop experience (Edge Chromium/WebView2).
- Exposes a folder picker API to the web app for native folder selection.
- Handles errors gracefully, including missing WebView2 runtime.

Notes:
- This launcher is intended for use with the desktop distribution of the TCGA Data Merger Tool.
- The web interface and all processing logic remain identical to the browser-based version.
- The folder picker button in the web UI only works when launched via this script.
- If port 5000 is unavailable, a random free port is used instead.
- Requires the Microsoft Edge WebView2 Runtime to be installed on Windows.
"""

import sys
import time
import socket
import threading
import webview
from tcga_web_app.app import app

class Api:
    """
    Exposes native APIs (e.g., folder picker) to the web UI via PyWebView's JS bridge.
    """
    def select_folder(self):
        """
        Opens a native folder selection dialog and returns the selected folder path.
        """
        return webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)

def find_free_port(preferred=5000):
    """
    Try to bind the preferred port; on failure, bind port=0 and return that.

    Args:
        preferred (int): Preferred port number (default 5000).

    Returns:
        int: The port number that was successfully bound.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', preferred))
        port = preferred
    except OSError:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    finally:
        s.close()
    return port

def wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    """
    Wait until a TCP connection to (host, port) succeeds, or timeout is reached.

    Args:
        host (str): Host address to connect to.
        port (int): Port number to connect to.
        timeout (float): Maximum time to wait in seconds.

    Returns:
        bool: True if the server is reachable, False if timeout is reached.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False

if __name__ == '__main__':
    # 1) pick a port (5000 if free, otherwise a random free one)
    port = find_free_port(preferred=5000)

     # 2) launch Flask on that port
    def start_flask():
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

    threading.Thread(target=start_flask, daemon=True).start()

    # 3) Wait up to 10s for it to bind
    if not wait_for_server('127.0.0.1', port):
        sys.exit("ERROR: Flask server failed to start on port {port}")

    # 4) Create and show the Edge-Chromium‐powered window
    try:
        webview.create_window(
            title="TCGA Data Merger Tool",
            url=f"http://127.0.0.1:{port}",
            width=1000,
            height=700,
            resizable=True,
            js_api=Api()
        )
        # gui='edgechromium' forces WebView2; http_server=True keeps our Flask server alive
        webview.start(gui='edgechromium', http_server=True)
    except Exception:
        sys.exit(
            "ERROR: Could not launch the native window.\n"
            "Please install the Microsoft Edge WebView2 Runtime:\n"
            "https://developer.microsoft.com/en-us/Microsoft-edge/webview2/?form=MA13LH#download"
        )
