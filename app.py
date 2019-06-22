# import the Flask class from the flask module
import os
from flask import Flask, render_template, send_from_directory, url_for

# create the application object
app = Flask(__name__)

# use decorators to link the function to a url
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/savassona')
def savassona():
	return render_template('savassona.html')

@app.route('/sant_joan')
def sant_joan():
	return render_template('sant_joan.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)