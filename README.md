# BetaLibrary
Your complement to bouldering guides. Check the beta provided by [MadBoulder](https://www.youtube.com/channel/UCX9ok0rHnvnENLSK7jdnXxA).

<p align="center">
<img src="/extras/general_preview.png">
Main Page
</p>

<p align="center">
<img src="/extras/preview.png">
Sector Map
</p>

## About

This project complements [MadBoulder](https://www.youtube.com/channel/UCX9ok0rHnvnENLSK7jdnXxA)'s beta video library and makes it easier to navigate through the available information. It is **NOT** a topo guide of bouldering areas and has no intention of becoming so. It is intended to be used along the bouldering guides of each area and its main goal is to simplify and ease the process of finding beta. 


## Usage

This project isn't hosted anywhere yet and hence it is not available through the web.

To build it locally follow the next steps: 
1. Make sure you have Python3, [Flask](http://flask.pocoo.org/) and [Folium](https://python-visualization.github.io/folium/) installed. I recomend to do so in a [virtual environment](https://virtualenv.pypa.io/en/latest/). (After cloning the repository you can install the required packages with: `$ pip install -r /path/to/requirements.txt`)
2. Clone the repository by tipying in a terminal `$ git clone https://github.com/juangallostra/BetaLibrary.git`
3. `cd` to `BetaLibrary` and run `$ python generate_templates.py`
4. Run `$ python app.py` and visit `http://127.0.0.1:5000/`
