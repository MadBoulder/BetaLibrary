# BetaLibrary
Locate where are the boulders listed in [MadBoulder](https://www.youtube.com/channel/UCX9ok0rHnvnENLSK7jdnXxA)'s Beta library.

<img src="/extras/preview.png" width="461" height="402">

## Usage
This project isn't hosted anywhere yet and hence it is not available through the web.

To build it locally follow the next steps: 
1. Make sure you have Python3, [Flask](http://flask.pocoo.org/) and [Folium](https://python-visualization.github.io/folium/) installed. I recomend to do so in a [virtual environment](https://virtualenv.pypa.io/en/latest/). (After cloning the repository you can install the required packages with: `$ pip install -r /path/to/requirements.txt`)
2. Clone the repository by tipying in a terminal `$ git clone https://github.com/juangallostra/BetaLibrary.git`
3. `cd` to `BetaLibrary` and run `$ python generate_templates.py`
4. Run `$ python app.py` and visit `http://127.0.0.1:5000/`
