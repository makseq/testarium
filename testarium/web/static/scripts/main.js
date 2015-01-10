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

function hideAll() {
	$('#header_back').hide();
	$('#body_back').hide();
	$('#header').hide();
	$('#main').hide();
}

$( document ).ready(function() {
	$( "#commit_table" ).draggable({ handle: ".table_header", cursor: "move" });
	$( "#graphline_back" ).draggable({ cancel: "#graphline", cursor: "move" });
	
	$('#commit_table').position({
		my: 'left top',
		at: 'left bottom',
		of: '#header_back',
		collision: 'fit'
	});
	
	/*$('#graphline_back').position({
		my: 'left top',
		at: 'right top',
		of: '#commit_table',
		collision: 'fit'
	});*/
	
	//c = new CommitTable();	
});

var app = angular.module('testarium', []);
app.controller('CommitController', ['$scope', '$http',
	function CommitTable($scope, $http) {
		$scope.index = 0;
		$scope.tables = [];
		$scope.loadCommits = function() {
			$http({
				url: "/api/commits", 
				method: "GET",
				params: { branch:"default", filter: "" },
			}).success(function(result) {
				$scope.tables.push({rows: result, cols: Object.keys(result[0])});
			});
		
			$scope.index++;
		}
	}]
);