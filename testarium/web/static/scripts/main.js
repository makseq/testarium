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

var GRID_SIZE = 10

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
        if (typeof s !== 'string') return false;
		return s.slice(0,7) === 'file://';
	},
	checkgraph: function(s) {
        if (typeof s !== 'string') return false;
		return s.slice(0,8) === 'graph://';
	},
	checkimage: function(s) {
        if (typeof s !== 'string') return false;
		return s.slice(0,8) === 'image://';
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
	var commits = $('#'+commits_id);
	var active_branch = commits.data('active-branch');
	var request = 'api/branches/'+active_branch+'/commits';
	var filter = commits.find('input').val();
	if (filter) request = 'api/branches/'+active_branch+'/commits?where='+filter;

	$.ajax({ url: request, dataType: 'json',
		success: function (data) {
			// refresh if data changed
			if (JSON.stringify(commits.data('scope')) !== JSON.stringify(data)) {
				l('update ' + commits_id );
				if (data.status < 0) {
					l(data)
				}

				// get running testarium processes

				commits.data('scope', data);
				commits.find('.body table').remove();
				commits.find('.body').append($("#commitsTableTemplate").render(data, true));

				// table body and footer widths
				var body = commits.children('.body').find('td');
				var footer = commits.children('.footer').find('th');
				for (var i = 0; i < body.length; i++) {
					var j = i % (footer.length - 1); // -1 is for close X
					$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
				}

				highlightRunningCommits(false);
			}
		}
	})
}

function highlightRunningCommits(auto_update){
	$.ajax({url: 'api/running', dataType:'json',
		success: function (data) {
            $('tr.commit-name').removeClass('running');
            for (var i = 0; i < data.result.length; i++) {
                var name = data.result[i];
                $('tr[data-commit-name="' + name + '"].commit-name').addClass('running');
            }
            if (auto_update) {
                setTimeout(function(){ highlightRunningCommits(true)}, 1000);
            }
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
	    if (data.result.length === 0) {
	        alert('No commits in branch: ' + branch);
	        return -1
        }

		data.id = 'commits-table-'+branch+scope.commits.number;
		data.active_branch = branch;

		// prepare header keys from all commit items
		var keys = [];
		for (var i=0; i<data.result.length; i++) {
			keys = keys.concat(Object.keys(data.result[i]));
		}
		var set = new Set(keys);
		data.header = Array.from(set);
		$('body').append($("#commitsDivTemplate").render(data, true));

		var commits = $('#' + data.id.replace(/(\+|=|\[|\]|\(|\)|\.)/g, '\\$1'));
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
		commits.draggable({ handle: ".header", grid:[GRID_SIZE,GRID_SIZE] });
		var span = commits.find('.header span');
		span.data('commits-table-id', data.id);
		span.dblclick(updateThisCommit);
		var input = commits.find('.header input');
		//input.outerWidth(commits.outerWidth()-span.outerWidth()-20);
		input.height(span.height());
		input.css({left: span.outerWidth()+20});
		input.data('commits-table-id', data.id);
		input.keyup(commitFilter);
		commits.resize(function() { input.outerWidth(commits.outerWidth()-span.outerWidth()-20); })
		commits.resize();

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
			scope.commits.active='';
		});

		// commits table position (it must be before scope.commits.active changed)
		if (scope.commits.active !== '') {
            var link = $('#' + scope.commits.active.replace(/(\+|=|\[|\]|\(|\)|\.)/g, '\\$1'));
            commits.css({top: link.offset().top + link.outerHeight() + GRID_SIZE*3, left: link.offset().left});
        }

		scope.commits.number++;
		var also = '#' + data.id;
		commits.children('.body').resizable({alsoResize: also, grid: GRID_SIZE});
		scope.commits.active=commits.attr('id');
		//setTimeout(commitUpdate, 2000, commits.attr('id'))

        // copy text if ctrl pressed
        commits.find('td').on('click', function(e){
             if (e.button === 0 && e.ctrlKey) {
                 clipboard_copy($(this).text());
                 e.preventDefault();
				 e.stopPropagation();
				 return false;
             }
        });

        // highlight running commits
        highlightRunningCommits(false);

        // add right click menu
        commits.contextMenu({
            selector: 'tr',
            items: {
                open_url: {name: "Open commit", icon: "fa-copy", "accesskey": "n",
                            callback: function(itemKey, opt, e) {
                                var path = $(opt.$trigger[0]).data("commit-path");
                                path = path.substring(0, path.indexOf("config.json"));  // remove "config.json"
                                window.open(path, $(opt.$trigger[0]).data("commit-name"));
                            }
                },

                sep0: "---------",

                copy_name: {name: "Copy name", icon: "fa-copy", "accesskey": "n",
                            callback: function(itemKey, opt, e) {
                                clipboard_copy($(opt.$trigger[0]).data("commit-name"));
                            }
                },
				copy_path: {name: "Copy path", icon: "fa-copy", "accesskey": "n",
                            callback: function(itemKey, opt, e) {
				                var path = $(opt.$trigger[0]).data("commit-path");
				                path = path.substring(path.indexOf("/")+1);  // remove root of path ("storage/")
                                path = path.substring(0, path.indexOf("config.json"));  // remove "config.json"
                                clipboard_copy(path);
                            }
                },
                copy_line: {name: "Copy row", icon: "fa-copy", "accesskey": "l",
                            callback: function(itemKey, opt, e) {
                                var cp = $(opt.$trigger[0]).text().replace(/\r?\n|\r/g, '');
                                clipboard_copy(cp);
                            }
                },

                sep1: "---------",

                delete: {name: "Delete commit", icon: "fa-trash", "accesskey": "d",
                         callback: function(itemKey, opt, e) {
                            var table = $(opt.$trigger[0]).closest('.commit-table');
                            var branch = table.data("activeBranch");
                            var name = $(opt.$trigger[0]).data("commit-name");
                            deleteCommit(branch, name, function() {
                            	commitUpdate(table.attr('id'));
                            });
                         }
                }
            }
        });

	}); // api/branch/name/commits
}

function newBranchDialog()
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

		// focus
		branches.attr('tabindex', -1);
		branches.on('focusin', focusWindow);
		branches.focus();
	})
}


function addCloseWindow(obj, data)
{
    function close_window() { $('#'+data.id).remove(); }
	obj.find('.close-button').click(close_window);
	obj.keydown(function(e) {
        if (e.keyCode === 27) close_window();

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

function showTips(e)
{
	var tips = $('#tips');
	tips.toggle();
	tips.draggable({ handle: ".header", grid: [GRID_SIZE, GRID_SIZE] });
	tips.on('focusin', focusWindow);
	tips.focus();

	$(this).dblclick(function(e){ e.stopPropagation() })

	var link = $('#'+scope.commits.active.replace(/(\+|=|\[|\]|\(|\)|\.)/g, '\\$1'));
	tips.css({top: link.offset().top + link.outerHeight() + GRID_SIZE*3, left: link.offset().left});
}

function saveComment(e)
{
	var branch = $(e.currentTarget).closest('.commit-table').data('activeBranch');
	var commitName = $(e.currentTarget).closest('.commit-name').data('commit-name');
	$.ajax({
			url:'api/branches/'+branch+'/commits/'+commitName+'?op=modify',
            data: {
			    comment: $(e.currentTarget).text()
            },
            method: 'POST',
			dataType: 'json'
        })
		.done(function(d) {
			if (d.status !== 0)
				alert('Something wrong in your comment. Do you use ASCII symbols only?\n\n' + JSON.stringify(d));
		})
}

function deleteCommit(branch, commitName, done)
{
	$.ajax({
			url:'api/branches/'+branch+'/commits/'+commitName+'?op=delete',
            method: 'POST',
			dataType: 'json'
        })
		.done(function(d) {
			if (d.status !== 0) {
			    console.log(d);
				alert('Something wrong with commit:\n\n' + d.msg);
			}
			done()
		})
}

function newPlot()
{
	var data = { id: 'plot-'+scope.plot.number };
	$('body').append($("#plotTemplate").render(data, true));

	var plot = $('#'+data.id);
	plot.data('window-type', 'plot');

	// close button handler
	addCloseWindow(plot, data);

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
	plot.draggable({ handle: ".header", grid: [GRID_SIZE, GRID_SIZE] });
	plot.bind('remove', function() {
		scope.plot.active='';
	});

	// get position of active commit table and set right corner for new plot
	var link = $('#'+scope.commits.active.replace(/(\+|=|\[|\]|\(|\)|\.)/g, '\\$1'));
	plot.css({top: link.offset().top, left: link.offset().left + link.outerWidth() + GRID_SIZE*3});
	scope.plot.number++;
	plot.focus()
}

function loadPlot(event, obj)
{
	var url = $(obj).data('url');
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
	plot.focus();
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

	// close button handler
	addCloseWindow(image, data);

	// focus
	image.attr('tabindex',-1);
	image.on('focusin', focusWindow);

	// drag
	image.draggable({ handle: ".header", grid: [GRID_SIZE, GRID_SIZE]});
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
	}

	// keydown left & right arrows
	image.keydown(function(e){
		if(e.keyCode == 27) close_window();
		if(e.keyCode == 37) image_scrolling($(this), -1);
		if(e.keyCode == 39) image_scrolling($(this), +1);
	});
	// mouse wheel
	image.mousewheel(function(e){
		if(e.deltaY < 0) image_scrolling($(this), -1);
		if(e.deltaY > 0) image_scrolling($(this), +1);
		e.preventDefault();
		e.stopPropagation();
	});

	// remove button background on commit table
	canvas.bind('remove', function () {
		var buttons = $(this).data('assigned-image-buttons');
		for (var i in buttons) {
			$('#' + buttons[i]).css('background', 'none')
		}
	});

	// get position of active commit table and set right corner for new image
	var link = $('#'+scope.commits.active.replace(/(\+|=|\[|\]|\(|\)|\.)/g, '\\$1'));
	image.css({top: link.offset().top, left: link.offset().left + link.outerWidth() + 30});
	scope.image.number++;
	image.focus()
}

function loadImage(event, obj)
{
	var url = $(obj).data('url') + '?rnd=' + Math.random();
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
	var imgs = canvas.find('img')
	imgs.hide() // hide all images
	imgs.each(function(o){
		if ($(this).attr('src') == url)
			$(this).remove();
	});
	canvas.append(
			'<a href="' + url + '" target=blank>' +
			'<img' +
				' style="border:' + backcolor + ' 1px solid"' +
				' src="' + url + '"/>' +
			'</a>');
	image = $('#'+scope.image.active);
	image.resizable({grid:GRID_SIZE});

	event.preventDefault();
	event.stopPropagation();
	return false
}


$( document ).ready(function() {
	$('.button.commits').click(newBranchDialog);
	$('.button.info').click(showInfo);
	$('#tips-btn').click(showTips);
	$('.button.plot-btn').click(newPlot);
	$('.button.image-btn').click(newImage);

	$.getJSON('api/branches/active', function(data) {
		newCommitTableByBranch(data.result);  // load active branch commit table
	});

	$('#control').dblclick(function(e){
		var tmp = $('html').css('background');
		$('html').css('background', prev_background);
		prev_background = tmp;
	});

	highlightRunningCommits(true);
});