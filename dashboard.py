from os.path import dirname, join
import json
import collections
import math
from datetime import date, datetime

import numpy as np
import pandas as pd

from bokeh.layouts import column, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, HoverTool, RangeSlider
from bokeh.models import  RadioButtonGroup, DataTable, TableColumn, CheckboxGroup
from bokeh.plotting import figure

from bokeh.models.callbacks import CustomJS

import handle_channel_data

SORT_FUNCTION = """
            function sortData(jsObj, sort_method, category, isRatio){
                var sortedArray = [];
                // Push each JSON Object entry in array by [key, value]
                for(var i in jsObj)
                {
                    if (isRatio)
                    {
                        sortedArray.push([i, jsObj[i][category]/jsObj[i]["count"]]);
                    } else {
                        sortedArray.push([i, jsObj[i][category]]);
                    }
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


def get_last_dashboard_update():
    return handle_channel_data.get_last_update_date()


def prepare_barchart_data(data, axis):
    """
    Group data by different categories so that it is ready
    to be plotted
    """
    processed_data = {}
    for _, v in axis.items():
        x_data = [datum[v] for datum in data]
        unique_x_data = set(x_data)
        data_subset = {'x': [], 'y': [], 'raw': {}}
        for datum in unique_x_data:
            data_subset['x'].append(datum)
            data_subset['y'].append(x_data.count(datum))
            data_subset['raw'][datum] = {
                'count': x_data.count(datum),
                'viewCount': sum([int(vid['stats'].get('viewCount', '0')) for vid in data if vid[v] == datum]),
                'favoriteCount': sum([int(vid['stats'].get('favoriteCount', '0')) for vid in data if vid[v] == datum]),
                'likeCount': sum([int(vid['stats'].get('likeCount', '0')) for vid in data if vid[v] == datum]),
                'dislikeCount': sum([int(vid['stats'].get('dislikeCount', '0')) for vid in data if vid[v] == datum]),
                'commentCount': sum([int(vid['stats'].get('commentCount', '0')) for vid in data if vid[v] == datum])
            }
        processed_data[v] = data_subset
    return processed_data


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
        video_data = handle_channel_data.get_data_firebase()['items']

    # X axis categories
    x_axis_map = {
        "Climber": "climber",
        "Zone": "zone",
        "Grade": "grade",
    }
    # Y axis categories
    y_axis_map = {
        "Count": "count",
        "Views": "viewCount",
        # "Favourites": "favoriteCount",
        "Likes": "likeCount",
        "Dislikes": "dislikeCount",
        "Comments": "commentCount"
    }

    # get ready to plot data
    barchart_data = prepare_barchart_data(video_data, x_axis_map)

    # html template to place the plots
    desc = Div(
        text=open(join(dirname(__file__), "templates/stats.html")).read(),
        sizing_mode="stretch_width"
    )

    # initial data source fill
    data_to_plot = barchart_data['grade']['raw']
    od = collections.OrderedDict(
        sorted(data_to_plot.items(), key=lambda x: x[0]))

    x_to_plot = np.array([key for key, val in od.items()])
    y_to_plot = np.array([val['count'] for key, val in od.items()])

    source = ColumnDataSource(data=dict(x=x_to_plot, y=y_to_plot))

    # Create Input controls
    label_slider = Slider(start=0, end=90, value=90,
                          step=1, title="Label Angle")
    range_slider = RangeSlider(title="Value Range", start=0, end=max(
        y_to_plot), value=(0, max(y_to_plot)), step=1)
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
        x_axis_map.keys()), value="Grade")
    y_axis = Select(title="Y Axis", options=sorted(
        y_axis_map.keys()), value="Count")
    checkbox = CheckboxGroup(
        labels=["Show ratio with respect to number of videos"], active=[])

    # show number of categories
    x_count_source = ColumnDataSource(
        data=dict(x_count=[len(x_to_plot)], category=[x_axis.value]))
    columns = [
        TableColumn(field="category", title="Category"),
        TableColumn(field="x_count", title="Count"),
    ]
    x_count_data_table = DataTable(
        source=x_count_source, columns=columns, width=320, height=280)

    # Generate the actual plot
    p = figure(x_range=x_to_plot, y_range=(0, max(y_to_plot)), plot_height=250, title="{} {}".format(x_axis.value, y_axis.value),
               toolbar_location="above")
    # Fill it with data and format it
    p.vbar(x='x', top='y', width=0.9, source=source)
    p.xaxis.major_label_orientation = math.pi/2
    p.add_tools(HoverTool(tooltips=[("name", "@x"), ("count", "@y")]))

    # Controls
    controls = [
        range_slider,
        min_year,
        max_year,
        sort_order,
        x_axis,
        y_axis,
        checkbox,
        label_slider,
        x_count_data_table
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

    # ratio checkbox
    checkbox_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            sort_order=sort_order,
            x_axis_map=x_axis_map,
            x_axis=x_axis,
            y_axis_map=y_axis_map,
            y_axis=y_axis,
            range_slider=range_slider,
            fig=p,
            title=p.title
        ),
        code=SORT_FUNCTION + """
            var data = o_data[x_axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            var is_ratio = cb_obj.active.length > 0;
            title.text = x_axis.value.concat(" ", y_axis.value);
            if (is_ratio)
            {
                title.text = x_axis.value.concat(" ", y_axis.value, " per video");   
            }
            // Sort data
            var sorted_data = sortData(data['raw'], sort_order.active, y_axis_map[y_axis.value], is_ratio);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                if (sorted_data[i][1] >= range_slider.value[0] && sorted_data[i][1] <= range_slider.value[1]) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1]);
                }
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.data['category'] = [x_axis.value];
            x_source.change.emit();
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
    checkbox.js_on_change('active', checkbox_callback)
    # range slider
    range_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            sort_order=sort_order,
            x_axis_map=x_axis_map,
            x_axis=x_axis,
            y_axis_map=y_axis_map,
            y_axis=y_axis,
            checkbox=checkbox,
            fig=p
        ),
        code=SORT_FUNCTION + """
            var data = o_data[x_axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            var is_ratio = checkbox.active.length > 0;
            // Sort data
            var sorted_data = sortData(data['raw'], sort_order.active, y_axis_map[y_axis.value], is_ratio);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                if (sorted_data[i][1] >= cb_obj.value[0] && sorted_data[i][1] <= cb_obj.value[1]) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1]);
                }
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.data['category'] = [x_axis.value];
            x_source.change.emit();
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
    # variable to group data
    x_axis_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            x_axis_map=x_axis_map,
            y_axis_map=y_axis_map,
            y_axis=y_axis,
            range_slider=range_slider,
            sort_order=sort_order,
            checkbox=checkbox,
            fig=p,
            title=p.title
        ),
        code=SORT_FUNCTION + """
            title.text = cb_obj.value.concat(" ", y_axis.value);
            var data = o_data[x_axis_map[cb_obj.value]];
            var x = data['x'];
            var y = data['y'];
            var is_ratio = checkbox.active.length > 0;
            if (is_ratio)
            {
                title.text = title.text.concat(" per video");   
            }
            var sorted_data = sortData(data['raw'], sort_order.active, y_axis_map[y_axis.value], is_ratio);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                new_x.push(sorted_data[i][0]);
                new_y.push(sorted_data[i][1]);
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.data['category'] = [cb_obj.value];
            x_source.change.emit();
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

    # variable to group data
    y_axis_callback = CustomJS(
        args=dict(
            source=source,
            x_source=x_count_source,
            o_data=barchart_data,
            x_axis_map=x_axis_map,
            x_axis=x_axis,
            y_axis_map=y_axis_map,
            range_slider=range_slider,
            sort_order=sort_order,
            checkbox=checkbox,
            fig=p,
            title=p.title
        ),
        code=SORT_FUNCTION + """
            title.text = x_axis.value.concat(" ", cb_obj.value);
            var data = o_data[x_axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            var is_ratio = checkbox.active.length > 0;
            if (is_ratio)
            {
                title.text = x_axis.value.concat(" ", cb_obj.value, " per video");   
            }
            var sorted_data = sortData(data['raw'], sort_order.active, y_axis_map[cb_obj.value], is_ratio);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                new_x.push(sorted_data[i][0]);
                new_y.push(sorted_data[i][1]);
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.data['category'] = [x_axis.value];
            x_source.change.emit();
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
            range_slider=range_slider,
            checkbox=checkbox,
            fig=p
        ),
        code=SORT_FUNCTION + """
            var data = o_data[x_axis_map[x_axis.value]];
            var x = data['x'];
            var y = data['y'];
            // Sort data
            var is_ratio = checkbox.active.length > 0;
            var sorted_data = sortData(data['raw'], cb_obj.active, y_axis_map[y_axis.value], is_ratio);
            console.log(sorted_data);
            var new_y = [];
            var new_x = [];
            for (var i = 0; i < x.length; i++) {
                if (sorted_data[i][1] >= range_slider.value[0] && sorted_data[i][1] <= range_slider.value[1]) {
                    new_x.push(sorted_data[i][0]);
                    new_y.push(sorted_data[i][1]);
                }
            }
            x_source.data['x_count'] = [new_x.length];
            x_source.data['category'] = [x_axis.value];
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
