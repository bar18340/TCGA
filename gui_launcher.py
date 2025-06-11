import webview
from tcga_web_app.app import app
from threading import Thread

class Api:
    def select_folder(self):
        return webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)

def start_flask():
    app.run(debug=False, port=5000, use_reloader=False)

if __name__ == '__main__':
    flask_thread = Thread(target=start_flask, daemon=True)
    flask_thread.start()

    api = Api()

    window = webview.create_window(
        title="TCGA Data Merger Tool",
        url="http://127.0.0.1:5000",
        width=1200,
        height=950,
        resizable=True,
        js_api=api
    )

    webview.start(gui=None, debug=False, http_server=True)
