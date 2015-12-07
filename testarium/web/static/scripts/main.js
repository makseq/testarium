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

var scope = {
	number: 0
}

function l(some) {
	console.log(some)
}

function focusWindow(e) {
	$('.window').css('z-index', 0)
	$(this).css('z-index', 1000)
}

function commitFilter(e) {
	commits = $('#'+$(this).data('commits-table-id'));
	data = commits.data('scope')

	request = 'api/branches/'+data.active_branch+'/commits';
	if ($(this).val()) request = 'api/branches/'+data.active_branch+'/commits?where='+$(this).val();

	$.getJSON(request, function (data) {
		commits.find('.body table').remove()
		commits.find('.body').append($("#commitsTableTemplate").render(data, true))

		// table body and footer widths
		body = commits.children('.body').find('td')
		footer = commits.children('.footer').find('th')
		for (var i = 0; i < body.length; i++) {
			var j = i % (footer.length-1) // -1 is for close X
			$(body.get(i)).outerWidth($(footer.get(j)).outerWidth())
		}
	})
}



function newCommitTable()
{
	$.getJSON('api/info', function(info) {
		info = info.result

		$.getJSON('api/branches/'+info.active_branch+'/commits', function (data) {
			data.id = 'commits-table-'+info.active_branch+scope.number
			data.active_branch = info.active_branch
			data.header = Object.keys(data.result[0])
			$('body').append($("#commitsDivTemplate").render(data, true))

			commits = $('#' + data.id)
			commits.data('scope', data)
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

			scope.number++
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


$( document ).ready(function() {
	$('.button.commits').click(newCommitTable)
	$('.button.info').click(showInfo)

});