import os
import socket
from flaskwebgui import FlaskUI
from threading import Thread
from tcga_web_app.app import app


def find_free_port():
    """Find a free localhost port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def run_flask(port):
    os.environ["PORT"] = str(port)
    app.run(debug=False, port=port, use_reloader=False)


if __name__ == '__main__':
    port = find_free_port()
    thread = Thread(target=run_flask, args=(port,))
    thread.daemon = True
    thread.start()

    FlaskUI(
        app=app,
        server="flask",
        port=port,
        width=1200,
        height=800,
        fullscreen=False,
        browser_path="C:/Program Files/Google/Chrome/Application/chrome.exe" 
            if os.path.exists("C:/Program Files/Google/Chrome/Application/chrome.exe") 
            else None
    ).run()
