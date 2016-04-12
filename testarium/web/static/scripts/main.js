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
	cleanfile: function(s) {
		return s.slice(7);
	},
	cleangraph: function(s) {
		return s.slice(8);
	}
})

var scope = {
	commits: {
		number: 0,
		active: ''
	},
	plot: {
		number: 0,
		active: '',
		plot_btn_number: 0
	}
}




// console log
function l(some) {
	console.log(some)
}

function focusWindow(e) {
	$('.window').css('z-index', 0)
	$(this).css('z-index', 1000)
	id = $(this).attr('id')
	switch($(this).data('window-type')) {
		case 'plot':	scope.plot.active=id; break;
		case 'commits':	scope.commits.active=id; break;
	}

}

function commitUpdate(commits_id) {
	commits = $('#'+commits_id);
	active_branch = commits.data('active-branch')
	request = 'api/branches/'+active_branch+'/commits';
	filter = commits.find('input').val()
	if (filter) request = 'api/branches/'+active_branch+'/commits?where='+filter;

	$.ajax({ url: request, dataType: 'json',
		success: function (data) {
			// refresh if data changed
			if (JSON.stringify(commits.data('scope')) != JSON.stringify(data)) {
				l('update ' + commits_id )
				if (data.status < 0) {
					l(data)
				}

				commits.data('scope', data)
				commits.find('.body table').remove()
				commits.find('.body').append($("#commitsTableTemplate").render(data, true))

				// table body and footer widths
				body = commits.children('.body').find('td')
				footer = commits.children('.footer').find('th')
				for (var i = 0; i < body.length; i++) {
					var j = i % (footer.length - 1) // -1 is for close X
					$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
				}
			}

			//setTimeout(commitUpdate, 2000, commits_id)
		}
	})
}

function commitFilter()
{
	commitUpdate($(this).data('commits-table-id'))
}

function newCommitTable()
{
	$.getJSON('api/branches', function(info) {
		var branch = prompt("Please enter branch name", info.result);
		if (branch == null) return

		$.getJSON('api/branches/'+branch+'/commits', function (data) {
			data.id = 'commits-table-'+branch+scope.commits.number
			data.active_branch = branch
			data.header = Object.keys(data.result[0])
			$('body').append($("#commitsDivTemplate").render(data, true))

			commits = $('#' + data.id)
			commits.data('scope', data)
			commits.data('active-branch', data.active_branch)
			commits.data('window-type', 'commits')
			commits.find('.body').append($("#commitsTableTemplate").render(data, true))

			// table body and footer widths
			body = commits.children('.body').find('td')
			footer = commits.children('.footer').find('th')
			for (var i = 0; i < body.length; i++) {
				var j = i % (footer.length-1) // -1 is for close X
				if ($(body.get(i)).outerWidth() > $(footer.get(j)).outerWidth())
					$(footer.get(j)).outerWidth($(body.get(i)).outerWidth())
				else
					$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
			}

			// header widths and input filter setup
			commits.draggable({ handle: ".header" });
			span = commits.find('.header span')
			input = commits.find('.header input')
			input.outerWidth(commits.outerWidth()-span.outerWidth()-20)
			input.height(span.height())
			input.css({left: span.outerWidth()+20})
			input.data('commits-table-id', data.id)
			input.keyup(commitFilter)

			// close button
			btn = commits.find('table th.close-button')
			width = commits.outerWidth()-(btn.offset().left-commits.offset().left)
			btn.width(width)
			btn.data('commits-table-id', data.id)
			btn.click(function(){ $('#'+$(this).data('commits-table-id')).remove() })

			// focus
			commits.attr('tabindex',-1);
			commits.on('focusin', focusWindow);

			// selected tr
			commits.find('.body table tbody tr').click(function(){
				$(this).toggleClass('selected')
			})

			// remove bind singal
			commits.bind('remove', function() {
				scope.commits.number--;
				scope.commits.active='';
			})

			scope.commits.number++
			commits.focusin();

			//setTimeout(commitUpdate, 2000, commits.attr('id'))
		}); // api/branch/name/commits
	}) // api/info
}


function showInfo()
{
	if ($('#info').is(":visible"))
		$('#info').hide()
	else
		$.getJSON('api/info', function(data) {
			$('#info pre').html(JSON.stringify(data.result, undefined, 4))
			$('#info').show()
		})
}

function newPlot()
{
	data = { id: 'plot-'+scope.plot.number }
	$('body').append($("#plotTemplate").render(data, true))

	plot = $('#'+data.id)
	plot.data('window-type', 'plot')

	close = plot.find('.close-button')
	close.data('plot-id', data.id)
	close.click(function(){ $('#'+$(this).data('plot-id')).remove(); })

	// focus
	plot.attr('tabindex',-1);
	plot.on('focusin', focusWindow);

	// drag
	plot.draggable({ handle: ".header" });
	plot.bind('remove', function() {
		scope.plot.number--;
		scope.plot.active='';
	})

	scope.plot.number++
	plot.focusin()
}

function loadPlot(event, obj)
{
	url = $(obj).data('url')
	if (scope.plot.active == '' )
		newPlot()

	// random color for plot line
	to = 200
	from = 40
	bright = to-from
	random = {r: from+Math.floor(Math.random()*bright), g: from+Math.floor(Math.random()*bright), b: from+Math.floor(Math.random()*bright)}
	backcolor = 'rgb('+random.r+','+random.g+','+random.b+')'
	$(obj).css('background-color', backcolor)

	$(obj).attr('id', 'commit-plot-btn-'+scope.plot.plot_btn_number)
	scope.plot.plot_btn_number++;

	plot = $('#'+scope.plot.active);
	plot.find('.header .name').text()
	canvas = $('#'+scope.plot.active+' .canvas');
	canvas.find('svg').remove()

	function done() {
		canvas.find('svg').data('assigned-plot-buttons', $(obj).attr('id'))
		canvas.find('svg').bind('remove', function () {
			plot_btn = $(this).data('assigned-plot-buttons')
			$('#' + plot_btn).css('background', 'none')
		})
	}

	d3LoadAndPlot(url, '#'+scope.plot.active+' .canvas', backcolor, done)
	event.preventDefault()
	event.stopPropagation()
	return false
}

$( document ).ready(function() {
	$('.button.commits').click(newCommitTable)
	$('.button.info').click(showInfo)
	$('.button.plot-btn').click(newPlot)

});