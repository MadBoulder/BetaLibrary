# import the Flask class from the flask module
from flask import Flask, render_template

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

# start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)