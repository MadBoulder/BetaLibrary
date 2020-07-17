from os.path import dirname, join
import json
import collections
import math
from datetime import date, datetime

import numpy as np
import pandas as pd

from bokeh.layouts import column, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, HoverTool, RangeSlider
from bokeh.models import  RadioButtonGroup, DataTable, TableColumn, CheckboxGroup, AutocompleteInput
from bokeh.plotting import figure

from bokeh.models.callbacks import CustomJS

import get_channel_data

SORT_FUNCTION = """
            function sortData(jsObj, sort_method, category){
                // Run native sort function and returns sorted array.
                if (sort_method === 0) {
                    return jsObj.sort();
                }
                if (sort_method === 1) {
                    return jsObj.sort(function(a, b) { return b[1][category] - a[1][category]; });
                }
                if (sort_method === 2) {
                    return jsObj.sort(function(a, b) { return a[1][category] - b[1][category]; });
                }
            }
"""


def get_last_dashboard_update():
    return get_channel_data.get_last_update_date()


def get_dashboard(local_data=False):
    # Load data
    video_data = {}
    if local_data:
        data = pd.json_normalize(pd.read_json(
            'data/channel/processed_data.json')['items'])
        with open('data/channel/processed_data.json', 'r') as f:
            data = json.load(f)
            video_data = data['items']
    else:
        video_data = get_channel_data.get_data_firebase()['items']

    # X axis categories
    x_axis_map = {
        "Title": "title",
    }
    # Y axis categories
    y_axis_map = {
        "Views": "viewCount",
        # "Favourites": "favoriteCount",
        "Likes": "likeCount",
        "Dislikes": "dislikeCount",
        "Comments": "commentCount"
    }

    # html template to place the plots
    desc = Div(
        text=open(join(dirname(__file__), "templates/stats.html")).read(),
        sizing_mode="stretch_width"
    )

    # initial data source fill
    barchart_data = { video['title']: video['stats'] for video in video_data }
    data_to_plot = barchart_data

    od = collections.OrderedDict(
        sorted(data_to_plot.items(), key=lambda x: x[0]))

    x_to_plot = np.array([key for key, val in od.items()])
    y_to_plot = np.array([int(val['viewCount']) for key, val in od.items()])

    source = ColumnDataSource(data=dict(x=x_to_plot, y=y_to_plot))

    # Create Input controls
    label_slider = Slider(start=0, end=90, value=90,
                          step=1, title="Label Angle")
    
    label_checkbox = CheckboxGroup(
        labels=["Show labels"], active=[])

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

    x_axis = Select(title="X Axis", options=sorted(
        x_axis_map.keys()), value="Title")

    y_axis = Select(title="Y Axis", options=sorted(
        y_axis_map.keys()), value="Views")

    # autocomplete inputs
    climbers = sorted(list({video['climber'] for video in video_data}))
    ac_climber = AutocompleteInput(
        title="Select Climber",
        value="",
        completions=climbers)
    

    zones = sorted(list({video['zone'] for video in video_data}))
    ac_zones = AutocompleteInput(
        title="Select Zone",
        value="",
        completions=zones)

    grades = sorted(list({video['grade'] for video in video_data}))
    ac_grades = AutocompleteInput(
        title="Select Grade",
        value="",
        completions=grades)

    # show number of categories
    x_count_source = ColumnDataSource(
        data=dict(x_count=[len(x_to_plot)], category=["Videos"]))
    columns = [
        TableColumn(field="category", title="Category"),
        TableColumn(field="x_count", title="Count"),
    ]
    x_count_data_table = DataTable(
        source=x_count_source, columns=columns, width=320, height=280)

    # Generate the actual plot
    p = figure(x_range=x_to_plot, y_range=(0, max(y_to_plot)), plot_height=250, title=y_axis.value,
               toolbar_location="above")
    
    # hide x axis
    p.xaxis.visible = False

    # Fill it with data and format it
    p.vbar(x='x', top='y', width=0.9, source=source)
    p.xaxis.major_label_orientation = math.pi/2
    p.add_tools(HoverTool(tooltips=[("name", "@x"), ("count", "@y")]))

    # Controls
    controls = [
        min_year,
        max_year,
        sort_order,
        y_axis,
        label_slider,
        label_checkbox,
        ac_climber,
        ac_zones,
        ac_grades,
        x_count_data_table,
    ]

    # Callbacks for controls
    label_callback = CustomJS(
        args=dict(
            axis=p.xaxis[0]
        ),
        code="""
        axis.major_label_orientation = cb_obj.value * Math.PI / 180;
        """
    )
    label_slider.js_on_change('value', label_callback)

    # variable to group data
    y_axis_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            x_axis_map=x_axis_map,
            x_axis=x_axis,
            y_axis_map=y_axis_map,
            sort_order=sort_order,
            fig=p,
            title=p.title
        ),
        code=SORT_FUNCTION + """
            title.text = cb_obj.value;
            var sorted_data = sortData(Object.entries(o_data), sort_order.active, y_axis_map[cb_obj.value]);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < sorted_data.length; i++) {
                new_x.push(sorted_data[i][0]);
                new_y.push(sorted_data[i][1][y_axis_map[cb_obj.value]]);
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.change.emit();
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

    y_axis.js_on_change('value', y_axis_callback)

    # sort order control
    sort_order_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            x_axis_map=x_axis_map,
            x_axis=x_axis,
            y_axis_map=y_axis_map,
            y_axis=y_axis,
            fig=p
        ),
        code=SORT_FUNCTION + """
            // Sort data
            var sorted_data = sortData(Object.entries(o_data), cb_obj.active, y_axis_map[y_axis.value]);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < sorted_data.length; i++) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1][y_axis_map[y_axis.value]]);
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.change.emit();
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
