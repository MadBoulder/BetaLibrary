from os.path import dirname, join
import json
import collections
import math

import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, TextInput, HoverTool, RangeSlider, RadioButtonGroup
from bokeh.plotting import figure
from bokeh.palettes import Spectral6

from bokeh.models.callbacks import CustomJS

SORT_FUNCTION = """
            function sortData(jsObj, sort_method){
                var sortedArray = [];
                // Push each JSON Object entry in array by [key, value]
                for(var i in jsObj)
                {
                    sortedArray.push([i, jsObj[i]]);
                }
                // Run native sort function and returns sorted array.
                if (sort_method === 0) {
                    return sortedArray.sort();
                }
                if (sort_method === 1) {
                    return sortedArray.sort(function(a, b) { return b[1] - a[1]; });
                }
                if (sort_method === 2) {
                    return sortedArray.sort(function(a, b) { return a[1] - b[1]; });
                }
            }
"""

def prepare_barchart_data(data, axis):
    """
    Group data by different categories so that it is ready
    to be plotted
    """
    processed_data = {}
    for k, v in axis.items():
        x_data = [datum[v].lower() for datum in data]
        unique_x_data = set(x_data)
        data_subset = {'x':[], 'y':[], 'raw':{}}
        for datum in unique_x_data:
            data_subset['x'].append(datum)
            data_subset['y'].append(x_data.count(datum))
            data_subset['raw'][datum] = x_data.count(datum)
        processed_data[v] = data_subset
    return processed_data

def get_dashboard():
    # Load data
    data = pd.json_normalize(pd.read_json('data/processed_data.json')['items']) 
    video_data = {}
    with open('data/processed_data.json', 'r') as f:
        video_data = json.load(f)['items']

    # X axis categories
    axis_map = {
        "Climber": "climber",
        "Zone": "zone",
        "Grade": "grade",
    }

    # get ready to plot data
    barchart_data = prepare_barchart_data(video_data, axis_map)

    # html template to place the plots
    desc = Div(
        text=open(join(dirname(__file__), "templates/stats.html")).read(),
        sizing_mode="stretch_width"
    )
    # this must be replaced by js
    sort_functions = {
        0: lambda x: x[0],
        1: lambda x: x[1],
        2: lambda x: -x[1]
    }
    # initial data source fill
    data_to_plot = barchart_data['grade']['raw']
    od = collections.OrderedDict(sorted(data_to_plot.items(), key=sort_functions[0]))

    x_to_plot = np.array([key for key, val in od.items()])
    y_to_plot = np.array([val for key, val in od.items()])

    source = ColumnDataSource(data=dict(x=x_to_plot, y=y_to_plot))

    # Create Input controls
    range_slider = RangeSlider(title="Value Range", start=0, end=max(y_to_plot), value=(0, max(y_to_plot)), step=1)
    min_year = Slider(title="From", start=2015, end=2020, value=2015, step=1)
    max_year = Slider(title="To", start=2015, end=2020, value=2020, step=1)
    sort_order = RadioButtonGroup(
        labels=[
            "Alphabetically",
            "Decreasing",
            "Increasing"
        ],
        active=0
    )
    x_axis = Select(title="X Axis", options=sorted(axis_map.keys()), value="Grade")
    y_axis = Select(title="Y Axis", options=["Count"], value="Count")

    # Generate the actual plot
    p = figure(x_range=x_to_plot, y_range=(0,max(y_to_plot)), plot_height=250, title="{} Count".format(x_axis.value),
            toolbar_location=None, tools="")
    # Fill it with data and format it
    p.vbar(x='x', top='y', width=0.9, source=source)
    p.xaxis.major_label_orientation = math.pi/2
    p.add_tools(HoverTool(tooltips=[("name", "@x"), ("count", "@y")]))

    # Controls
    controls = [range_slider, min_year, max_year, sort_order, x_axis, y_axis]
    
    # Callbacks for controls
    range_callback = CustomJS(
        args=dict(
            source=source,
            o_data=barchart_data,
            sort_order=sort_order,
            axis_map=axis_map,
            x_axis=x_axis,
            fig=p
        ),
        code=SORT_FUNCTION + """
            var data = o_data[axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            // Sort data
            var sorted_data = sortData(data['raw'], sort_order.active);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                if (sorted_data[i][1] >= cb_obj.value[0] && sorted_data[i][1] <= cb_obj.value[1]) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1]);
                }
            }
            source.data['x'] = new_x;
            source.data['y'] = new_y;
            source.change.emit();
            fig.x_range.factors = [];
            fig.x_range.factors = new_x;
            if (Array.isArray(new_y) && new_y.length) {
                fig.y_range.end = Math.max.apply(Math, new_y);
            }
        """
    )
    range_slider.js_on_change('value', range_callback)

    x_axis_callback = CustomJS(
        args=dict(
            source=source,
            o_data=barchart_data,
            axis_map=axis_map,
            range_slider=range_slider,
            sort_order=sort_order,
            fig=p
        ),
        code=SORT_FUNCTION + """
            var data = o_data[axis_map[cb_obj.value]];
            var x = data['x'];
            var y = data['y'];
            var sorted_data = sortData(data['raw'], sort_order.active);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                new_x.push(sorted_data[i][0]);
                new_y.push(sorted_data[i][1]);
            }
            source.data['x'] = new_x;
            source.data['y'] = new_y;
            source.change.emit();
            fig.x_range.factors = [];
            fig.x_range.factors = new_x;
            if (new_y && Array.isArray(new_y) && new_y.length) {
                range_slider.value = [0, Math.max.apply(Math, new_y)]; 
                range_slider.end = Math.max.apply(Math, new_y);
                fig.y_range.end = Math.max.apply(Math, new_y);
            }
        """
    )
    
    x_axis.js_on_change('value', x_axis_callback)

    sort_order_callback = CustomJS(
        args=dict(
            source=source,
            o_data=barchart_data,
            axis_map=axis_map,
            x_axis=x_axis,
            range_slider=range_slider,
            fig=p
        ),
        code=SORT_FUNCTION + """
            var data = o_data[axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            // Sort data
            var sorted_data = sortData(data['raw'], cb_obj.active);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                if (sorted_data[i][1] >= range_slider.value[0] && sorted_data[i][1] <= range_slider.value[1]) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1]);
                }
            }
            source.data['x'] = new_x;
            source.data['y'] = new_y;
            source.change.emit();
            fig.x_range.factors = [];
            fig.x_range.factors = new_x;
            if (new_y && Array.isArray(new_y) && new_y.length) {
                fig.y_range.end = Math.max.apply(Math, new_y);
            }
        """
    )

    sort_order.js_on_change('active', sort_order_callback)

    # Define layout
    inputs = column(*controls, width=320, height=1000)
    inputs.sizing_mode = "fixed"
    l = layout([
        [desc],
        [inputs, p],
    ], sizing_mode="scale_both")

    return l