$(window).load(function(){
	var left = $("tr.htmldiff").first().children()[0];
	var right = $("tr.htmldiff").first().children()[1];
	annotateDiffs(left, right);
	alignChanges();
	addToolTips();
});

var FRIENDLY_CONTAINER_NAMES = {
	'table': 'Table',
	'tr': 'Table row',
	'td': 'Table cell',
	'th': 'Table header',
	'p': 'Paragraph',
	'span': 'Span',
	'div': 'Div',
	'a': 'Link',
	'h1': 'Heading (level 1)',
	'h2': 'Heading (level 2)',
	'h3': 'Heading (level 3)',
	'h4': 'Heading (level 4)',
	'h5': 'Heading (level 5)',
	'ul': 'Unordered list',
	'ol': 'Ordered list',
	'li': 'List item',
	'img': 'Image'
};

var FRIENDLY_STYLE_NAMES = {
	'strong': 'Bold',
	'b': 'Bold',
	'em': 'Italics',
	'i': 'Italics',
	'u': 'Underline',
	's': 'Strikethrough'
};

var FRIENDLY_ATTRIBUTE_NAMES = {
	'href': 'destination',
	'class': 'class',
	'style': 'style',
	'src': 'source'
};

// object comparison from http://stackoverflow.com/a/1144249/5126
function equal(x, y)
{
  var p;
  for(p in y) {
      if(typeof(x[p])=='undefined') {return false;}
  }

  for(p in y) {
      if (y[p]) {
          switch(typeof(y[p])) {
              case 'object':
                  if (!equal(y[p], x[p])) { return false; } break;
              case 'function':
                  if (typeof(x[p])=='undefined' ||
                      (y[p].toString() != x[p].toString()))
                      return false;
                  break;
              default:
                  if (y[p] != x[p]) { return false; }
          }
      } else {
          if (x[p])
              return false;
      }
  }

  for(p in x) {
      if(typeof(y[p])=='undefined') {return false;}
  }

  return true;
};

function visualSort(a, b)
{
	var aPos = $(a).position(), bPos = $(b).position();
	return aPos.top != bPos.top ? aPos.top - bPos.top : aPos.left - bPos.left;
}

function addToolTips() {
	var current = -1;
	var toolBar = false, changeText, prev, next;
	var showChange = function(index){
		if(current > -1 && current != index)
			$(changes[current]).qtip('api').hide();
		current = index;
		if(!toolBar)
		{
			toolBar = $('<div class="diff-toolbar"></div>');
			changeText = $('<span class="diff-toolbar-text"/>').appendTo(toolBar);
			prev = $('<input type="button" class="little" value="Previous" />').click(goPrev)
				.appendTo(toolBar);
			next = $('<input type="button" class="little" value="Next" />').click(goNext)
				.appendTo(toolBar);
			$('<span class="close-button" title="Close">&times;</span>').click(function(){
				toolBar.animate({ 'margin-top': '-36px'}, function(){ toolBar.hide(); });
			}).css('cursor', 'pointer').appendTo(toolBar);
			toolBar.appendTo(document.body).hide();
		}
		$(changes[current]).data('qtip').show();
		changeText.empty().append('Change ' + (current + 1) + ' of ' + changes.length);
		var tipTop = Math.min($(changes[current]).data('qtip').elements.tooltip.position().top,
							  $(changes[current]).position().top);
		$('html,body').animate({ scrollTop: tipTop - 40 },
							function(){
								if(toolBar.is(':hidden'))
									toolBar.show().animate({ 'margin-top': '0px' });
							});
		prev.attr('disabled', current == 0);
		next.attr('disabled', current == changes.length-1);
	};
	var goNext = function() {
		if(current + 1 <= changes.length - 1)
			showChange(current + 1);
		else showChange(current);
	};
	var goPrev = function() {
		if(current - 1 >= 0)
			showChange(current - 1);
		else showChange(current);
	};
	$('<span class="button">Review changes</span>)')
		.click(function(){
			showChange(0);
		}).insertBefore($('tr.htmldiff').parents('table').first())
		  .wrap('<div class="review-changes">')
		  .parent().append('You can use the &larr; and &rarr; keys, too.');
	var changes = $("del.diff-html-removed,ins.diff-html-added,span.diff-html-changed")
		.sort(visualSort)
		.each(function (index){
			$(this).data('changeIndex', index);
		})
		.qtip({
			content: function (api) {
				switch(api.elements.target[0].nodeName)
				{
					case 'DEL': return 'Content was deleted';
					case 'INS': return 'Content was added';
					default : return decodeURIComponent(
								api.elements.target.first().attr('changes'));
				}
			},
			position: {
				my: 'bottom center',
				at: 'top center'
			},
			hide: 'unfocus mouseleave',
			events: {
				show: function(event, api) {
					if(api.elements.target.is('.diff-html-changed'))
						api.elements.target.addClass('diff-highlight');
				},
				hide: function(event, api) {
					var willHide = !event.originalEvent
						|| event.originalEvent.type == 'mousedown'
						|| !toolBar
						|| toolBar.is(':hidden')
						|| changes[current] != api.elements.target[0];
					if(willHide)
						api.elements.target.removeClass('diff-highlight');
					return willHide;
				}
			}
		})
		.click(function(){
			showChange($(this).data('changeIndex'));
		});

	$(document).keydown(function (evt){
		if(evt.which == 39) // right arrow
			goNext();
		if(evt.which == 37) // left arrow
			goPrev();
	});
}

function getWords(elems)
{
	if(!elems.length)
		elems = [elems];
	var words = [], elem;
	for ( var i = 0; elems[i]; i++ ) {
		elem = elems[i];
		if ( elem.nodeType === 3) {
			words = words.concat(elem.nodeValue.split(/\s+/));
		} else if ( elem.nodeType === 1 && elem.nodeName != 'DEL' && elem.nodeName != 'INS') {
			words = words.concat(getWords(elem.childNodes));
		}
	}
	return words;
}

function wordNodeMap(root)
{
	var map = [];
	$(root).children().each(function (index, elem){
		$.each(getWords(elem), function(index, word){
			word && map.push({ text: word, node: elem});
		});
	});
	return map;
}

function alignChanges(elem)
{
	var left = $("tr.htmldiff").first().children()[0];
	var right = $("tr.htmldiff").first().children()[1];
	var leftText = wordNodeMap(left);
	var rightText = wordNodeMap(right);
	for(var i = 0; i < leftText.length && i < rightText.length; i++)
	{
		var leftNode = leftText[i].node;
		var rightNode = rightText[i].node;
		if($(leftNode).data('aligned') || $(rightNode).data('aligned'))
			continue;
		align(leftNode, rightNode);
	}
}

function align(a, b)
{
	var aPos = $(a).position().top;
	var bPos = $(b).position().top;
	if(aPos != bPos)
	{
		var higher = aPos < bPos ? a : b;
		$(higher).before($('<div/>').height(Math.abs(aPos - bPos)));
	}
	$(a).data('aligned', true);
	$(b).data('aligned', true);
}

function getContentNodes(node)
{
	return $(node).contents().map(function (index, elem){
		if(elem.nodeType === 3 || elem.nodeName.toLowerCase() == 'img')
			return elem;
		else
			return getContentNodes(elem);
	}).get();
}

function contentNodesToString(nodes)
{
	return $.map(nodes, function (node){
		return nodeToText(node);
	}).join('');
}

function nodeToText(node)
{
	if(node.nodeType === 3)
		return node.nodeValue;
	return '';
}

function annotateDiffs(oldVersion, newVersion)
{
	var oldContent = getContentNodes(oldVersion);
	var newContent = getContentNodes(newVersion);
	var oldText = contentNodesToString(oldContent);
	var newText = contentNodesToString(newContent);
	var dmp = new diff_match_patch();
	var textDiff = dmp.diff_main(oldText, newText);
	var diffMap = mapDiffToDom(oldContent, newContent, textDiff);
	$.each(diffMap, function(index, piece){
		switch(piece[0])
		{
			case DIFF_EQUAL:
				var changes = styleChanges(piece[1], piece[2]);
				if(changes.length)
				{
					var span = $('<span class="diff-html-changed"></span>');
					var changeList = "<ul class='changelist'><li>";
					changeList += changes.join('</li><li>') + '</li></ul>';
					span.attr('changes', changeList);
					$(piece[2]).wrap(span);
				}
				break;
			case DIFF_DELETE:
				$(piece[1]).wrap('<del class="diff-html-removed"></del>');
				break;
			case DIFF_INSERT:
				$(piece[1]).wrap('<ins class="diff-html-added"></ins>');
				break;
		}
	});
}

function attributes(node)
{
	var attr = [];
	var len = node.attributes.length, a;
	for (a = 0; a < len; a++) {
		attr.push([node.attributes[a].name.toLowerCase(), node.attributes[a].value]);
	}
	return attr;
}


function styles(node)
{
	return $(node).parents().map(function (index, elem){
		return {'tag': elem.nodeName.toLowerCase(), 'attrs': attributes(elem)};
	});
}

function describeStyle(style, delete_or_insert)
{
	var description;
	if(FRIENDLY_STYLE_NAMES[style.tag])
	{
		var style_name = "<b>" + FRIENDLY_STYLE_NAMES[style.tag] + "</b>";
		description = style_name + " style added";
		if(delete_or_insert == DIFF_DELETE)
			description = style_name + " style removed";
		return description;
	}
	description = "Moved out of"
	if(delete_or_insert == DIFF_INSERT)
		description = "Moved into";
	var container_name = FRIENDLY_CONTAINER_NAMES[style.tag] || style.tag;
	description += " <b>" + container_name + "</b>";
	if(style.attrs.length)
	{
		description += " with " + $.map(style.attrs, function(attr){
			var attr_name = FRIENDLY_ATTRIBUTE_NAMES[attr[0]] || attr[0];
			return attr_name + " " + attr[1];
		}).join(' and ');
	}
	return description;
}

function styleChanges(oldNode, newNode)
{
	var changes = [];
	var oldStyles = styles(oldNode);
	var newStyles = styles(newNode);
	$.each(newStyles, function(index, newStyle){
		$.each(oldStyles, function(i, oldStyle){
			if(!newStyle || !oldStyle)
				return;
			if(equal(newStyle, oldStyle))
			{
				delete newStyles[index];
				delete oldStyles[i];
				return false;
			}
		});
	});
	$.each(oldStyles, function(index, style){
		if(style)
			changes.push(describeStyle(style, DIFF_DELETE));
	});
	$.each(newStyles, function(index, style){
		if(style)
			changes.push(describeStyle(style, DIFF_INSERT));
	});
	return changes;
}

function splitNodeIfTooLong(node, len, arr)
{
	if(node.nodeValue.length > len)
	{
		var remaining = node.splitText(len);
		arr.push(remaining);
	}
}

function splitDiffIfTooLong(diff, len, arr)
{
	if(diff[1].length > len)
	{
		arr.push([diff[0], diff[1].slice(len)]);
		diff[1] = diff[1].slice(0, len);
	}
}

/*
 * Aligns text to node and diff boundaries, splitting where necessary (in the
 * DOM itself as well), and makes one unified map that connects both sides of
 * the diff. Destroys the maps to save space.
 */
function mapDiffToDom(left, right, diff)
{
	left = left.reverse(); // use as stack but want to start from the front
	right = right.reverse();
	diff = diff.reverse();
	var map = [];
	var imagesLeft = [];
	var imagesRight = [];
	
	while(diff.length)
	{
		var diffSlice = diff.pop();
		// TODO: Need to find a better way to compare images.
		// For now, throw them into two lists and compare lists after this loop.
		var leftNode, rightNode;
		do {
			leftNode = left.pop();
			if(leftNode && leftNode.nodeName == 'IMG')
				imagesLeft.push(leftNode);
		} while(leftNode && leftNode.nodeType != 3);
		do {
			rightNode = right.pop();
			if(rightNode && rightNode.nodeName == 'IMG')
				imagesRight.push(rightNode);
		} while(rightNode && rightNode.nodeType != 3);
		switch(diffSlice[0]){
			case DIFF_EQUAL:
				var shortest = Math.min(diffSlice[1].length,
										leftNode.nodeValue.length,
										rightNode.nodeValue.length);
				splitNodeIfTooLong(leftNode, shortest, left);
				splitNodeIfTooLong(rightNode, shortest, right);
				splitDiffIfTooLong(diffSlice, shortest, diff);
				map.push([DIFF_EQUAL, leftNode, rightNode]);
				break;
			case DIFF_DELETE:
				right.push(rightNode);
				var shortest = Math.min(diffSlice[1].length,
										leftNode.nodeValue.length);
				splitNodeIfTooLong(leftNode, shortest, left);
				splitDiffIfTooLong(diffSlice, shortest, diff);
				map.push([DIFF_DELETE, leftNode]);
				break;
			case DIFF_INSERT:
				left.push(leftNode);
				var shortest = Math.min(diffSlice[1].length,
										rightNode.nodeValue.length);
				splitNodeIfTooLong(rightNode, shortest, right);
				splitDiffIfTooLong(diffSlice, shortest, diff);
				map.push([DIFF_INSERT, rightNode]);
				break;
		}
	}
	$.each(imagesRight, function(index, rightImg){
		var rightSrc = $(rightImg).attr('src');
		var found = false;
		$.each(imagesLeft, function(i, leftImg){
			if(!rightImg || !leftImg)
				return;
			if(rightSrc == $(leftImg).attr('src'))
			{
				found = true;
				map.push([DIFF_EQUAL, leftImg, rightImg]);
				delete imagesRight[index];
				delete imagesLeft[i];
				return false;
			}
		});
		if(!found)
			map.push([DIFF_INSERT, rightImg]);
	});
	$.each(imagesLeft, function(i, leftImg){
		if(leftImg)
			map.push([DIFF_DELETE, leftImg]);
	});
	return map;
}
