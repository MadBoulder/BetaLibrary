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

@app.route('/all')
def all():
	return render_template('all.html')

@app.route('/about_us')
def about():
	return render_template('about_us.html')

@app.route('/savassona')
def savassona():
	return render_template('savassona.html')

@app.route('/sant_joan')
def sant_joan():
	return render_template('sant_joan.html')

@app.route('/la_comarca')
def la_comarca():
	return render_template('la_comarca.html')

@app.route('/can_bruguera')
def can_bruguera():
	return render_template('can_bruguera.html')


# start the server
if __name__ == '__main__':
    app.run(debug=True)