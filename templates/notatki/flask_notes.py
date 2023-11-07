from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


# THEN THIS INTO TERMINAL
#   set FLASK_APP=main.py

# if you want to run from win terminal
# flask --app <filename> run


@app.route("/username/<name>/1")
def hello_name(name):
    return f"<p>Hello, {name}!</p>"


# <name> will become the variable passed into the function
# so the address is http://127.0.0.1:5000/username/John/1
# variables can be also integers. It's set with <int:variable>


@app.route("/number/<int:number>")
def number(number):
    if number == 2:
        return "<h1>YES</h1>"
    return "<h1>NO</h1>"


# if number in /number/<number> == 2 it will return YES, if not it will return NO

# if you put htmls into templates and images, js, css into static folder then you can server them with flask like this
from flask import render_template


@app.route("/")
def home():
    return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run()

# this runs server from python file
