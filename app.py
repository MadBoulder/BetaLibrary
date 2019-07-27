import os
from flask import Flask, render_template, send_from_directory

# create the application object
app = Flask(__name__)

# Load favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images/logo'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# use decorators to link the function to a url
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/<string:area>')
def render_area(area):
	return render_template(area + ".html")

# start the server
if __name__ == '__main__':
    app.run(debug=True)