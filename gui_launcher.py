import sys
import time
import socket
import threading
import webview
from tcga_web_app.app import app

class Api:
    def select_folder(self):
        return webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)

def find_free_port(preferred=5000):
    """Try to bind preferred port; on failure bind port=0 and return that."""
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
    """Return True once we can TCP-connect to (host,port), else False after timeout."""
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
