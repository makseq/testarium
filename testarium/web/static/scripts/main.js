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

$.ajaxSetup({ cache: false });

/*** jsRender stuff ***/
var vars = {};
$.views.tags({
    setvar: function(key, value) {
        vars[key] = value;
    }
});
$.views.helpers({
    getvar: function(key) {
        return vars[key];
    },
	getvarfile: function(key) {
        return vars[key].slice(7);
    },
	getvargraph: function(key) {
		return vars[key].slice(8);
	},
	checkfile: function(s) {
		return s.slice(0,7) == 'file://';
	},
	checkgraph: function(s) {
		return s.slice(0,8) == 'graph://';
	},
	checkimage: function(s) {
		return s.slice(0,8) == 'image://';
	},
	cleanfile: function(s) {
		return s.slice(7);
	},
	cleangraph: function(s) {
		return s.slice(8);
	},
	cleanimage: function(s) {
		return s.slice(8);
	}
});

var scope = {
	commits: {
		number: 0,
		active: ''
	},
	plot: {
		number: 0,
		active: '',
		plot_btn_number: 0
	},
	image: {
		number: 0,
		active: '',
		image_btn_number: 0
	},
	branches: {
		number: 0
	}
};

var prev_background = '#FFF';


// console log
function l(some) {
	console.log(some)
}

function focusWindow(e) {
	$('.window').css('z-index', 0);
	$(this).css('z-index', 1000);
	id = $(this).attr('id');
	switch($(this).data('window-type')) {
		case 'plot':	scope.plot.active=id; break;
		case 'commits':	scope.commits.active=id; break;
		case 'image':	scope.image.active=id; break;
	}
}

function commitUpdate(commits_id) {
	commits = $('#'+commits_id);
	active_branch = commits.data('active-branch');
	request = 'api/branches/'+active_branch+'/commits';
	filter = commits.find('input').val();
	if (filter) request = 'api/branches/'+active_branch+'/commits?where='+filter;

	$.ajax({ url: request, dataType: 'json',
		success: function (data) {
			// refresh if data changed
			if (JSON.stringify(commits.data('scope')) != JSON.stringify(data)) {
				l('update ' + commits_id );
				if (data.status < 0) {
					l(data)
				}

				commits.data('scope', data);
				commits.find('.body table').remove();
				commits.find('.body').append($("#commitsTableTemplate").render(data, true));

				// table body and footer widths
				body = commits.children('.body').find('td');
				footer = commits.children('.footer').find('th');
				for (var i = 0; i < body.length; i++) {
					var j = i % (footer.length - 1); // -1 is for close X
					$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
				}
			}

			//setTimeout(commitUpdate, 2000, commits_id)
		}
	})
}

function updateThisCommit()
{
	commitUpdate($(this).data('commits-table-id'))
}

function commitFilter()
{
	commitUpdate($(this).data('commits-table-id'))
}

function newCommitTableByBranch(branch)
{
	$.getJSON('api/branches/'+branch+'/commits', function (data) {
		data.id = 'commits-table-'+branch+scope.commits.number;
		data.active_branch = branch;
		data.header = Object.keys(data.result[0]);
		$('body').append($("#commitsDivTemplate").render(data, true));

		var commits = $('#' + data.id);
		commits.data('scope', data);
		commits.data('active-branch', data.active_branch);
		commits.data('window-type', 'commits');
		commits.find('.body').append($("#commitsTableTemplate").render(data, true));

		// table body and footer widths
		var body = commits.children('.body').find('td');
		var footer = commits.children('.footer').find('th');
		for (var i = 0; i < body.length; i++) {
			var j = i % (footer.length-1); // -1 is for close X
			if ($(body.get(i)).outerWidth() > $(footer.get(j)).outerWidth())
				$(footer.get(j)).outerWidth($(body.get(i)).outerWidth());
			else
				$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
		}

		// header widths and input filter setup
		commits.draggable({ handle: ".header" });
		var span = commits.find('.header span');
		span.data('commits-table-id', data.id);
		span.dblclick(updateThisCommit);
		var input = commits.find('.header input');
		input.outerWidth(commits.outerWidth()-span.outerWidth()-20);
		input.height(span.height());
		input.css({left: span.outerWidth()+20});
		input.data('commits-table-id', data.id);
		input.keyup(commitFilter);

		// close button
		var btn = commits.find('table th.close-button');
		var width = commits.outerWidth()-(btn.offset().left-commits.offset().left);
		btn.width(width);
		btn.data('commits-table-id', data.id);
		btn.click(function(){ $('#'+$(this).data('commits-table-id')).remove() });

		// focus
		commits.attr('tabindex',-1);
		commits.on('focusin', focusWindow);

		// selected tr
		commits.find('.body table tbody tr').click(function(){
			$(this).toggleClass('selected')
		});

		// remove bind singal
		commits.bind('remove', function() {
			//scope.commits.number--;
			scope.commits.active='';
		});

		scope.commits.number++;
		commits.children('.body').resizable();
		scope.commits.active=commits.attr('id');
		//setTimeout(commitUpdate, 2000, commits.attr('id'))
	}); // api/branch/name/commits
}

function newCommitTable()
{
	$.getJSON('api/branches', function(info) {
		info.id = 'branches-'+scope.branches.number;
		scope.branches.number++;

		$('body').append($("#branchesTemplate").render(info, true));
		var branches = $('#'+info.id);
		branches.draggable({ handle: ".header" });

		var close = branches.find('.close-button');
		close.data('branches-id', info.id);
		close.click(function(){ $('#'+$(this).data('branches-id')).remove(); });

		var items = branches.find('.item');
		items.data('branches-id', info.id);
		items.click(function(){
			newCommitTableByBranch($(this).text());
			 $('#'+$(this).data('branches-id')).remove();
		});

		//var branch = prompt("Please enter branch name", info.result);
		//if (branch == null) return;
		//
	})
}


function showInfo()
{
	if ($('#info').is(":visible"))
		$('#info').hide();
	else
		$.getJSON('api/info', function(data) {
			$('#info pre').html(JSON.stringify(data.result, undefined, 4));
			$('#info').show()
		})
}

function saveComment(e)
{
	var branch = $(e.currentTarget).closest('.commit-table').data('activeBranch');
	var commitName = $(e.currentTarget).closest('.commit-name').data('commit-name')
	$.ajax('api/branches/'+branch+'/commits/'+commitName+'?op=modify&comment='+$(e.currentTarget).text())
}

function newPlot()
{
	var data = { id: 'plot-'+scope.plot.number };
	$('body').append($("#plotTemplate").render(data, true));

	var plot = $('#'+data.id);
	plot.data('window-type', 'plot');

	var close = plot.find('.close-button');
	close.data('plot-id', data.id);
	close.click(function(){ $('#'+$(this).data('plot-id')).remove(); });

	var change_plot = plot.find('.change-plot-button');
	change_plot.data('plot-id', data.id);
	change_plot.click(function(){
		$('#'+$(this).data('plot-id')+' .xy_plot').toggle();
		$('#'+$(this).data('plot-id')+' .xtyt_plot').toggle();
	});


	// focus
	plot.attr('tabindex',-1);
	plot.on('focusin', focusWindow);

	// drag
	plot.draggable({ handle: ".header", grid: [25, 25] });
	plot.bind('remove', function() {
		scope.plot.active='';
	});

	// get position of active commit table and set right corner for new plot
	var link = $('#'+scope.commits.active);
	plot.css({top: link.offset().top, left: link.offset().left + link.outerWidth() + 30});
	scope.plot.number++;
	plot.focusin()
}

function loadPlot(event, obj)
{
	url = $(obj).data('url');
	if (scope.plot.active == '' )
		newPlot();

	// random color for plot line
	var to = 255;
	var from = 0;
	var bright = to-from;
	var random = {r: from+Math.floor(Math.random()*bright), g: from+Math.floor(Math.random()*bright), b: from+Math.floor(Math.random()*bright)};
	var backcolor = 'rgb('+random.r+','+random.g+','+random.b+')';
	$(obj).css('background-color', backcolor);

	$(obj).attr('id', 'commit-plot-btn-'+scope.plot.plot_btn_number);
	scope.plot.plot_btn_number++;

	var plot = $('#'+scope.plot.active);
	plot.find('.header .name').text();
	var canvas = $('#'+scope.plot.active+' .canvas');
	canvas.find('svg').remove();

	// save active buttons in commit table
	var buttons = canvas.data('assigned-plot-buttons');
	if (typeof(buttons) != 'undefined')
		buttons.push($(obj).attr('id'));
	else
		buttons = [$(obj).attr('id')];
	canvas.data('assigned-plot-buttons', buttons);

	// disable background of plot button in commit table
	function done() {
		canvas.bind('remove', function () {
			var buttons = $(this).data('assigned-plot-buttons');
			for (var i in buttons) {
				$('#' + buttons[i]).css('background', 'none')
			}
		})
	}

	d3LoadAndPlot(url, '#'+scope.plot.active+' .canvas', backcolor, done);
	event.preventDefault();
	event.stopPropagation();
	return false
}

function newImage()
{
	var data = { id: 'image-'+scope.image.number };
	$('body').append($("#imageTemplate").render(data, true));

	var image = $('#'+data.id);
	image.data('window-type', 'image');

	var close = image.find('.close-button');
	close.data('image-id', data.id);
	close.click(function(){ $('#'+$(this).data('image-id')).remove(); });

	// focus
	image.attr('tabindex',-1);
	image.on('focusin', focusWindow);

	// drag
	image.draggable({ handle: ".header", grid: [25, 25] });
	image.bind('remove', function() {
		scope.image.active='';
	});

	// image scrolling
	var canvas = image.find('.canvas')
	function image_scrolling(e, increment) {
		imgs = $(e.find('.canvas')[0]).find('img');

		// found last visible image
		var i;
		for (i=0; i<imgs.length; i++)
			if ($(imgs[i]).is(":visible"))
				break

		// next image to show
		next = i+increment;
		if (next < 0) next = 0
		if (next >= imgs.length) next = imgs.length-1
		imgs.hide()
		$(imgs[next]).show()
	};
	// keydown left & right arrows
	image.keydown(function(e){
		if(e.keyCode == 37) image_scrolling($(this), -1);
		if(e.keyCode == 39) image_scrolling($(this), +1);
	})
	// mouse wheel
	image.mousewheel(function(e){
		if(e.deltaY < 0) image_scrolling($(this), -1);
		if(e.deltaY > 0) image_scrolling($(this), +1);
		e.preventDefault();
		e.stopPropagation();
	})

	// remove button background on commit table
	canvas.bind('remove', function () {
		var buttons = $(this).data('assigned-image-buttons');
		for (var i in buttons) {
			$('#' + buttons[i]).css('background', 'none')
		}
	})

	// get position of active commit table and set right corner for new image
	var link = $('#'+scope.commits.active);
	image.css({top: link.offset().top, left: link.offset().left + link.outerWidth() + 30});
	scope.image.number++;
	image.focusin()
}

function loadImage(event, obj)
{
	url = $(obj).data('url');
	if (scope.image.active == '' )
		newImage();

	// random color for image line
	var to = 255;
	var from = 0;
	var bright = to-from;
	var random = {r: from+Math.floor(Math.random()*bright), g: from+Math.floor(Math.random()*bright), b: from+Math.floor(Math.random()*bright)};
	var backcolor = 'rgb('+random.r+','+random.g+','+random.b+')';
	$(obj).css('background-color', backcolor);

	$(obj).attr('id', 'commit-image-btn-'+scope.image.image_btn_number);
	scope.image.image_btn_number++;

	var image = $('#'+scope.image.active);
	var canvas = $('#'+scope.image.active+' .canvas');

	// save active buttons in commit table
	var buttons = canvas.data('assigned-image-buttons');
	if (typeof(buttons) != 'undefined')
		buttons.push($(obj).attr('id'));
	else
		buttons = [$(obj).attr('id')];
	canvas.data('assigned-image-buttons', buttons);

	// add images
	imgs = canvas.find('img')
	imgs.hide() // hide all images
	imgs.each(function(o){
		if ($(this).attr('src') == url)
			$(this).remove();
	})
	canvas.append(
			'<a href="' + url + '" target=blank>' +
			'<img' +
				' style="border:' + backcolor + ' 1px solid"' +
				' src="' + url + '"/>' +
			'</a>')
	image = $('#'+scope.image.active)
	image.resizable({grid: 25})

	event.preventDefault();
	event.stopPropagation();
	return false
}


$( document ).ready(function() {
	$('.button.commits').click(newCommitTable);
	$('.button.info').click(showInfo);
	$('.button.plot-btn').click(newPlot);
	$('.button.image-btn').click(newImage);

	$.getJSON('api/branches/active', function(data) {
		newCommitTableByBranch(data.result);  // load active branch commit table
	});

	$('#control').dblclick(function(e){
			var tmp = $('html').css('background');
			$('html').css('background', prev_background);
			prev_background = tmp;
	})
});