from os.path import dirname, join
import json
import collections
import math

import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, TextInput, HoverTool, RangeSlider, CheckboxButtonGroup
from bokeh.plotting import figure
from bokeh.palettes import Spectral6

from bokeh.models.callbacks import CustomJS


def get_dashboard():
    # Load data
    data = pd.json_normalize(pd.read_json('data/processed_data.json')['items']) 

    video_data = {}
    with open('data/processed_data.json', 'r') as f:
        video_data = json.load(f)['items']

    axis_map = {
        "Climber": "climber",
        "Zone": "zone",
        "Grade": "grade",
    }

    desc = Div(
        text=open(join(dirname(__file__), "templates/stats.html")).read(),
        sizing_mode="stretch_width"
    )

    sort_functions = {
        0: lambda x: x[0],
        1: lambda x: x[1],
        2: lambda x: -x[1]
    }

    # Create Input controls
    range_slider = RangeSlider(title="Value Range", start=0, end=200, value=(0,200), step=1)
    min_year = Slider(title="From", start=2015, end=2020, value=2015, step=1)
    max_year = Slider(title="To", start=2015, end=2020, value=2020, step=1)
    sort_order = CheckboxButtonGroup(
        labels=[
            "Alphabetically",
            "Increasing",
            "Decreasing"
        ],
        active=[0]
    )

    x_axis = Select(title="X Axis", options=sorted(axis_map.keys()), value="Grade")
    y_axis = Select(title="Y Axis", options=["Count"], value="Count")

    # fill source
    x_data = [v[axis_map[x_axis.value]].lower() for v in video_data]
    unique_x_data = set(x_data)
    data_to_plot = {}
    for datum in unique_x_data:
        data_to_plot[datum] = x_data.count(datum)

    od = collections.OrderedDict(sorted(data_to_plot.items(), key=sort_functions[sort_order.active[0]]))

    x_to_plot = np.array([key for key, val in od.items()])
    y_to_plot = np.array([val for key, val in od.items()])

    source = ColumnDataSource(data=dict(x=x_to_plot, y=y_to_plot))
    og_source = ColumnDataSource(data=dict(x=x_to_plot, y=y_to_plot))

    range_slider.end = max(y_to_plot)

    p = figure(x_range=x_to_plot, y_range=(0,max(y_to_plot)), plot_height=250, title="{} Count".format(x_axis.value),
            toolbar_location=None, tools="")

    p.vbar(x='x', top='y', width=0.9, source=source)
    p.xaxis.major_label_orientation = math.pi/2
    p.add_tools(HoverTool(tooltips=[("name", "@x"), ("count", "@y")]))

    def select_data(new):
        x_data = [v[axis_map[x_axis.value]].lower() for v in video_data]
        unique_x_data = set(x_data)
        data_to_plot = {}
        for datum in unique_x_data:
            data_to_plot[datum] = x_data.count(datum)
        od = collections.OrderedDict(
            sorted(data_to_plot.items(), key = sort_functions[sort_order.active[0]])
        )
        # filters
        if new in axis_map.keys():
            # range should be recomputed
            new_max_y = list([v for k,v in od.items()])
            if new_max_y:
                range_slider.end = max(new_max_y)
            range_slider.value = (range_slider.start, range_slider.end)

        od_to_plot = collections.OrderedDict()
        for k, v in od.items():
            if int(v) >= range_slider.value[0] and int(v) <= range_slider.value[1]:
                od_to_plot[k] = v

        x_to_plot = np.array([key for key, val in od_to_plot.items()])
        y_to_plot = np.array([val for key, val in od_to_plot.items()])

        return {'x': x_to_plot, 'y': y_to_plot, 'max_y': max([v for k,v in od.items()])}

    def update_sort(old):
        new_data = select_data("")
        data_to_plot = {}
        for i in range(len(new_data['x'])):
            data_to_plot[new_data['x'][i]] = new_data['y'][i]
    
        od = collections.OrderedDict(
            sorted(data_to_plot.items(), key = sort_functions[sort_order.active[0]])
        )
        try:
            if len(sort_order.active) > 1:
                sort_order.active.remove(old[0])
        except:
            pass
        # filters
        od_filtered = collections.OrderedDict()
        for k, v in od.items():
            if int(v) >= range_slider.value[0] and int(v) <= range_slider.value[1]:
                od_filtered[k] = v

        od_to_plot = collections.OrderedDict(
            sorted(od_filtered.items(), key = sort_functions[sort_order.active[0]])
        )
        new_data_y = list(new_data['y'])
        if new_data_y:
            p.y_range.end = max(new_data_y)

        source.data = dict(
            x=np.array([k for k,v in od_to_plot.items()]),
            y=np.array([v for k,v in od_to_plot.items()]),
        )
        p.x_range.factors = []
        p.x_range.factors = [k for k,v in od_to_plot.items()]

    def update(new):
        new_data = select_data(new)
        x_name = axis_map[x_axis.value]
        y_name = "Count"

        p.xaxis.axis_label = x_axis.value
        p.yaxis.axis_label = y_axis.value
    
        p.x_range.factors = []
        p.x_range.factors = list(new_data['x'])
        new_data_y = list(new_data['y'])
        if new_data_y:
            p.y_range.end = max(new_data_y)
        range_slider.end = new_data['max_y']

        p.title.text = "{} Count".format(x_axis.value)
        source.data = dict(
            x=new_data['x'],
            y=new_data['y'],
        )
        p.tools = []
        p.add_tools(HoverTool(tooltips=[("name", "@x"), ("count", "@y")]))

    # Plot
    controls = [range_slider, min_year, max_year, x_axis, y_axis]
    for control in controls:
        control.on_change('value', lambda attr, old, new: update(new))

    callback_test = CustomJS(args=dict(source=source, og_source=og_source, fig=p), code="""
        var data = og_source.data;
        var f = cb_obj.value
        var x = data['x'];
        var y = data['y'];
        var new_y = [];
        var new_x = [];
        for (var i = 0; i < x.length; i++) {
            if (y[i] >= f[0] && y[i] <= f[1]) {
                new_x.push(x[i]);
                new_y.push(y[i]);
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
    """)

    range_slider.js_on_change('value', callback_test)

    sort_order.on_change('active', lambda attr, old, new: update_sort(old))

    controls = controls[0:3] + [sort_order] + controls[3:]

    inputs = column(*controls, width=320, height=1000)
    inputs.sizing_mode = "fixed"
    l = layout([
        [desc],
        [inputs, p],
    ], sizing_mode="scale_both")

    return l