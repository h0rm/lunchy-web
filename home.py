from flask import Flask, render_template
from lunchy import Lunchy

app = Flask(__name__)
lunchy = Lunchy()

@app.context_processor
def inject_stage_and_region():
    menu = lunchy.menu()
    return menu

@app.route("/")
def home():
    # return lunchy.menu()
    return render_template("home.html")
    
@app.route("/update")
def update():
    lunchy.updateMenu()
    return render_template("home.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)