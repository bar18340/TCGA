from flaskwebgui import FlaskUI
from tcga_web_app.app import app

# Launch Flask app in a desktop GUI window
ui = FlaskUI(app=app, server="flask", width=1024, height=768)
ui.run()
