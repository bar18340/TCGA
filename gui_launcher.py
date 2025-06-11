import webview
import threading
import time
import webbrowser
from tcga_web_app.app import app

class Api:
    def select_folder(self):
        return webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)

def start_flask():
    app.run(debug=False, port=5000, use_reloader=False)

def launch_gui():
    try:
        # Try to launch the GUI with edgechromium (modern, no .NET)
        api = Api()
        window = webview.create_window(
            title="TCGA Data Merger Tool",
            url="http://127.0.0.1:5000",
            width=1000,
            height=700,
            resizable=True,
            js_api=api
        )
        webview.start(gui='edgechromium', debug=False, http_server=True)
    except Exception as e:
        # Fallback: open the app in the default browser
        print("GUI backend failed. Falling back to browser:", e)
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    launch_gui()
