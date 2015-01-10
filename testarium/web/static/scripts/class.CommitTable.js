/*var CommitTable = function() {
	this.commits = {};
	this.name = 'commits';
	this.update('default');
}

CommitTable.prototype.update = function(branchName) {
	$.ajax({
		type: "get",
		url: "/api/commits",
		data: { branch:branchName, filter: "" },
		context: this
	})
	.success(function( data ) {
		this.commits = data;
		this.draw();
	});	
}

CommitTable.prototype.draw = function() {
	$('<table/>', {id : this.name}).appendTo('#workspace');
	//for (var i=0; i<this.commits.length; i++) {
	console.log( this.commits )
	for (i in this.commits) {
		$('<tr/>', { text: 'Hello'}).appendTo('#'+this.name);
	}
}
*/


