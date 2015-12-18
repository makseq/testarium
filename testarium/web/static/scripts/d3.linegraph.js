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

function d3LoadAndPlot(url, place_id, color, done)
{
	$.getJSON(url, function (plotdata) {
		if ('xAxis' in plotdata && 'yAxis' in plotdata)
			d3ShowGraph(plotdata.data, 'False Alarm', 'False Reject', place_id, color)
		else
			d3ShowGraph(plotdata, 'X', 'Y', place_id, color)

		done();
	})
}

function d3ShowGraph(plotdata, xAxisName, yAxisName, place, color)
{

	var svg;
	var xAxis, yAxis;
	var data = 	{ "x":[0, 0.5], "y":[0, 1] };
	var line, points, x, y;
	var colors = ['black', color, 'red', 'purple', 'green']
	var someAxis = [{'x':0, 'y':0, 't':0}, {'x':0, 'y':1, 't':0}, {'x':0, 'y':0, 't':0}, {'x':1, 'y':0, 't':0}]
	data = [someAxis, plotdata];


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
	points = svg.selectAll('.dots')
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
			return colors[d.index%colors.length];
		})
		.attr("transform", function(d) {
			return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
		)
		.append("svg:title")
		.text(function(d) { return xAxisName + ' = ' + d.point.x.toFixed(5)  + '\n'+ yAxisName + ' = ' + d.point.y.toFixed(5) + '\n' + 'Threshold = ' + d.point.t.toFixed(5); });

		$(place).show();
}

