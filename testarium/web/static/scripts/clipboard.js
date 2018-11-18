function clipboard_copy(text) {
	var textarea = document.createElement('textarea');
	textarea.textContent = text;
	document.body.appendChild(textarea);

	var selection = document.getSelection();
	var range = document.createRange();
	range.selectNode(textarea);
	selection.removeAllRanges();
	textarea.focus();
	textarea.setSelectionRange(0, textarea.value.length);
    document.execCommand('copy');
	selection.removeAllRanges();

	document.body.removeChild(textarea);
}
