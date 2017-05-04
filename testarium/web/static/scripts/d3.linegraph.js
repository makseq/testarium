/*
Testarium
Copyright (C) 2014 Maxim Tkachenko

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*var __links = document.querySelectorAll('a');
function __linkClick(e) { parent.window.postMessage(this.href, '*');};
for (var i = 0, l = __links.length; i < l; i++) {
	if ( __links[i].getAttribute('target') == '_blank' ) {
		__links[i].addEventListener('click', __linkClick, false);
	}
}*/
var change_button = typeof testarium_web == 'undefined';

function d3LoadAndPlot(url, place_id, color, done)
{
	$.getJSON(url, function (plotdata) {
		if (change_button) {
			if ($(place_id + ' .change-button').length == 0) {
				$(place_id).append('<div class="change-button" style="cursor:pointer;text-weight:bold; font-size:150%;">∿</div>');
				$(place_id + ' .change-button').click(function () {
					$(place_id + ' .xy_plot').toggle();
					$(place_id + ' .xtyt_plot').toggle();
				});
			}
		}

		if ($(place_id + ' .xy_plot').length == 0) $(place_id).append('<div class="xy_plot"></div>');
		if ($(place_id + ' .xtyt_plot').length == 0) $(place_id).append('<div class="xtyt_plot"></div>');


		var place = place_id + ' .xy_plot';
		if ('xAxis' in plotdata && 'yAxis' in plotdata)
			d3ShowGraphXY(plotdata.data, plotdata.xAxis, plotdata.yAxis, place, color);
		else
			d3ShowGraphXY(plotdata, 'X', 'Y', place, color);

		place = place_id + ' .xtyt_plot';
		if ('xAxis' in plotdata && 'yAxis' in plotdata)
			d3ShowGraphXTYT(plotdata.data, 'T', plotdata.xAxis + ' | '+  plotdata.yAxis, place, color);
		else
			d3ShowGraphXTYT(plotdata, 'T', 'X | Y', place, color);

		$(place).hide();
		done();
	})
}




function d3ShowGraph(plotdata, xAxisName, yAxisName, place, color)
{
	var svg;
	var xAxis, yAxis;
	var line, x, y;
	var someAxis = [{'x':0, 'y':0, 't':0}, {'x':0, 'y':1, 't':0}, {'x':0, 'y':0, 't':0}, {'x':1, 'y':0, 't':0}];
	var data = $(place).data('data');
	var colors = $(place).data('colors');

	if (typeof(data) == 'undefined') {
		data = [someAxis, plotdata];
		colors = ['black', color]
	}
	else {
		data.push(plotdata);
		colors.push(color)
	}
	$(place).data('data', data);
	$(place).data('colors', colors);


	//************************************************************
	// Create Margins and Axis and hook our zoom function
	//************************************************************
	var margin = {top: 10, right: 10, bottom: 50, left: 50},
		width = 500 - margin.left - margin.right,
		height = 500 - margin.top - margin.bottom;

	x = d3.scale.linear()
		.domain([0, 1])
		.range([0, width]);

	y = d3.scale.linear()
		.domain([0, 1])
		.range([height, 0]);

	xAxis = d3.svg.axis()
		.scale(x)
		.tickSize(-height)
		.tickPadding(10)
		.tickSubdivide(true)
		.orient("bottom");

	yAxis = d3.svg.axis()
		.scale(y)
		.tickPadding(10)
		.tickSize(-width)
		.tickSubdivide(true)
		.orient("left");

	var zoom = d3.behavior.zoom()
		.x(x)
		.y(y)
		.scaleExtent([1, 150])
		.on("zoom",
			function zoomed() {
				d3.select(this).select(".x.axis").call(xAxis);
				d3.select(this).select(".y.axis").call(yAxis);
				d3.select(this).selectAll('path.line').attr('d', line);

				d3.select(this).selectAll('.dots').selectAll('circle').attr("transform", function(d) {
					return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
				);
			}
		);


	//************************************************************
	// Generate our SVG object
	//************************************************************

	svg = d3.select(place).append("svg")
		.call(zoom)
		.attr("width", width + margin.left + margin.right)
		.attr("height", height + margin.top + margin.bottom)
		.append("g")
		.attr("transform", "translate(" + margin.left + "," + margin.top + ")");

	svg.append("g")
		.attr("class", "x axis")
		.attr("transform", "translate(0," + height + ")")
		.call(xAxis);

	svg.append("g")
		.attr("class", "y axis")
		.call(yAxis);


	svg.append("g")
		.attr("class", "x axis")
		.append("text")
		.attr("class", "axis-label")
		.attr("x", width/2-38)
		.attr("y", height+34)
		.text(xAxisName);

	svg.append("g")
		.attr("class", "y axis")
		.append("text")
		.attr("class", "axis-label")
		.attr("transform", "rotate(-90)")
		.attr("x", -height/2-30)
		.attr("y", (-margin.left)+14)
		.text(yAxisName);


	svg.append("clipPath")
		.attr("id", "clip")
		.append("rect")
		.attr("width", width)
		.attr("height", height);

	//************************************************************
	// Create D3 line object and draw data on our SVG object
	//************************************************************
	line = d3.svg.line()
		.interpolate("linear")
		.x(function(d) { return x(d.x); })
		.y(function(d) { return y(d.y); });

	svg.selectAll('.line')
		.data(data)
		.enter()
		.append("path")
		.attr("class", function(d,i){ return i==0 ? 'axisinner line' : 'line'; })
		.attr("clip-path", "url(#clip)")
		.attr('stroke', function(d,i){ return colors[i%colors.length]; })
		.attr("d", line);


	//************************************************************
	// Draw points on SVG object based on the data given
	//************************************************************
	var points = svg.selectAll('.dots')
		.data(data)
		.enter()
		.append("g")
		.attr("class", "dots")
		.attr("clip-path", "url(#clip)");

	points.selectAll('.dot')
		.data(function(d, index){
			var a = [];
			d.forEach(function(point,i){
				a.push({'index': index, 'point': point});
			});
			return a;
		})
		.enter()
		.append('circle')
		.attr('class', function(d,i){ return d.index==0 ? '' : 'dot' })
		.attr("r", function(d,i){ return d.index==0? 0.0 : 1.0 })
		.attr('fill', function(d,i){
			return colors[d.index % colors.length];
		})
		.attr("transform", function(d) {
			return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
		)
		.append("svg:title")
		.text(function(d) { return xAxisName + ' = ' + d.point.x.toFixed(5)  + '\n'+ yAxisName +
				' = ' + d.point.y.toFixed(5) + '\n' +
				'Threshold = ' + d.point.t.toFixed(5); });

	$(place).show();
}








function d3base(place, xAxisName, yAxisName, obj, data_obj)
{
	// get min & max for scaling
	function get_minmax(data, name) {
		var tmp_max, tmp_min, max = data[0][0][name], min = data[0][0][name];
		for (i = 0; i < data.length; i++) {
			tmp_max = Math.max.apply(Math, data[i].map(function (o) { return o[name]; }));
			tmp_min = Math.min.apply(Math, data[i].map(function (o) { return o[name]; }));
			if (max < tmp_max) max = tmp_max;
			if (min > tmp_min) min = tmp_min;
		}
		return {min: min, max: max};
	}
	var x_scale = get_minmax(data_obj.data, 'x');
	var y_scale = get_minmax(data_obj.data, 'y');

	var someAxis = [
		[{'x':0, 'y':y_scale.min, 't':0},
		{'x':0, 'y':y_scale.max, 't':0}],
		[{'x':x_scale.min, 'y':0, 't':0},
		{'x':x_scale.max, 'y':0, 't':0}]
	];
	data_obj.data = someAxis.concat(data_obj.data);
	data_obj.colors = ['black', 'black'].concat(data_obj.colors);
	var data = data_obj.data;
	var colors = data_obj.colors;

	//************************************************************
	// Create Margins and Axis and hook our zoom function
	//************************************************************
	var margin = {top: 10, right: 10, bottom: 50, left: 70},
			width = 500 - margin.left - margin.right,
			height = 500 - margin.top - margin.bottom;

	var x = d3.scale.linear()
			.domain([x_scale.min, x_scale.max])
			.range([0, width]);

	var y = d3.scale.linear()
			.domain([y_scale.min, y_scale.max])
			.range([height, 0]);

	var xAxis = d3.svg.axis()
			.scale(x)
			.tickSize(-height)
			.tickPadding(10)
			.tickSubdivide(true)
			.orient("bottom");

	var yAxis = d3.svg.axis()
			.scale(y)
			.tickPadding(10)
			.tickSize(-width)
			.tickSubdivide(true)
			.orient("left");

	var zoom = d3.behavior.zoom()
			.x(x)
			.y(y)
			.scaleExtent([1, 150])
			.on("zoom",
					function zoomed() {
						d3.select(this).select(".x.axis").call(xAxis);
						d3.select(this).select(".y.axis").call(yAxis);
						d3.select(this).selectAll('path.line').attr('d', obj.line);

						d3.select(this).selectAll('.dots').selectAll('circle').attr("transform", function(d) {
							return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
						);
					}
			);


	//************************************************************
	// Generate our SVG object
	//************************************************************

	var svg = d3.select(place).append("svg")
			.call(zoom)
			.attr("width", width + margin.left + margin.right)
			.attr("height", height + margin.top + margin.bottom)
			.append("g")
			.attr("transform", "translate(" + margin.left + "," + margin.top + ")");

	svg.append("g")
			.attr("class", "x axis")
			.attr("transform", "translate(0," + height + ")")
			.call(xAxis);

	svg.append("g")
			.attr("class", "y axis")
			.call(yAxis);


	svg.append("g")
			.attr("class", "x axis")
			.append("text")
			.attr("class", "axis-label")
			.attr("x", width/2-38)
			.attr("y", height+34)
			.text(xAxisName);

	svg.append("g")
			.attr("class", "y axis")
			.append("text")
			.attr("class", "axis-label")
			.attr("transform", "rotate(-90)")
			.attr("x", -height/2-30)
			.attr("y", (-margin.left)+14)
			.text(yAxisName);


	svg.append("clipPath")
			.attr("id", "clip")
			.append("rect")
			.attr("width", width)
			.attr("height", height);


	//************************************************************
	// Create D3 line object and draw data on our SVG object
	//************************************************************
	function line_clicked() {
		dash = prompt("Enter dash style for line", "3, 3");
		d3.select(this).style("stroke-dasharray", (dash));
	}

	obj.line = d3.svg.line()
		.interpolate("linear")
		.x(function(d) { return x(d.x); })
		.y(function(d) { return y(d.y); });

	svg.selectAll('.line')
		.data(data)
		.enter()
		.append("path")
		.attr("class", function(d,i){ return i==0 ? 'axisinner line' : 'line'; })
		.attr("clip-path", "url(#clip)")
		.attr('stroke', function(d,i){ return colors[i%colors.length]; })
		.attr("d", obj.line)
		.on('click', line_clicked);

	//************************************************************
	// Draw points on SVG object based on the data given
	//************************************************************
	var points = svg.selectAll('.dots')
		.data(data)
		.enter()
		.append("g")
		.attr("class", "dots")
		.attr("clip-path", "url(#clip)");

	points.selectAll('.dot')
		.data(function(d, index){
			var a = [];
			d.forEach(function(point,i){
				a.push({'index': index, 'point': point});
			});
			return a;
		})
		.enter()
		.append('circle')
		.attr('class', function(d,i){ return d.index==0 ? '' : 'dot' })
		.attr("r", function(d,i){ return d.index==0? 0.0 : 1.0 })
		.attr('fill', function(d,i){
			return colors[d.index % colors.length];
		})
		.attr("transform", function(d) {
			return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
		)
		.append("svg:title")
		.text(function(d) { return xAxisName + ' = ' + d.point.x.toFixed(5)  + '\n'+ yAxisName +
				' = ' + d.point.y.toFixed(5) + '\n' +
				yAxisName + ' = ' + d.point.t.toFixed(5); });


	obj.svg = svg;
	obj.xAxis = xAxis;
	obj.yAxis = yAxis;
	obj.x = x;
	obj.y = y;
	obj.place = place;
	return obj;
}



function d3ShowGraphXY(plotdata, xAxisName, yAxisName, place, color)
{
	var data = $(place).data('data');
	var colors = $(place).data('colors');
	var svg, x, y, line;

	if (typeof(data) == 'undefined') {
		data = [plotdata];
		colors = [color];
	}
	else {
		data.push(plotdata);
		colors.push(color);
	}
	$(place).data('data', data);
	$(place).data('colors', colors);

	// base d3 init
	var obj = {line: line};
	var data_obj = {data: data, colors: colors}; // make ref to data
	obj = d3base(place, xAxisName, yAxisName, obj, data_obj); // add axis to data in d3base
	data = data_obj.data;
	colors = data_obj.colors;
	svg = obj.svg;
	x = obj.x;
	y = obj.y;
	xAxis = obj.xAxis;
	yAxis = obj.yAxis;

	$(place).show();
}


function d3ShowGraphXTYT(plotdata, xAxisName, yAxisName, place, color)
{
	var data = $(place).data('data2');
	var colors = $(place).data('colors2');


	// make 2 plot (t,x) and (t,y) from one (x,y,t) plot
	var newplotdata = [];
	newplotdata.push([]);
	var k = newplotdata.length-1;
	for (var i=0; i<plotdata.length; i++){
		newplotdata[k][i] = {x:plotdata[i].t, y:plotdata[i].y, t:plotdata[i].x}
	}
	newplotdata.push([]);
	k = newplotdata.length-1;
	for (i=0; i<plotdata.length; i++){
		newplotdata[k][i] = {x:plotdata[i].t, y:plotdata[i].x, t:plotdata[i].y}
	}
	plotdata = newplotdata;

	// add data from previous plots
	if (typeof(data) == 'undefined') {
		data = plotdata;
		colors = [color, color];
	}
	else {
		data = data.concat(plotdata);
		colors.push(color);
		colors.push(color);
	}
	$(place).data('data2', data);
	$(place).data('colors2', colors);


	// base init
	var obj = {line: null};
	var data_obj = {data: data, colors:colors}; // make ref to data
	d3base(place, xAxisName, yAxisName, obj, data_obj); // add axis to data in d3base

	$(place).show();
}
