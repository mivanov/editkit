import html5lib
from html5lib import treebuilders, treewalkers, serializer
from diff_match_patch import diff_match_patch
from xml import dom

DELETE = diff_match_patch.DIFF_DELETE
EQUAL = diff_match_patch.DIFF_EQUAL
INSERT = diff_match_patch.DIFF_INSERT



def parse_fragment(html):
    p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    tree = p.parseFragment(html)
    return tree


def serialize(tree):
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(tree)
    s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
    output_generator = s.serialize(stream)
    return ''.join(output_generator)


def diff_text(old, new):
    dmp = diff_match_patch()
    dmp.Diff_Timeout = 0.01
    dmp.Diff_EditCost = 4
    diff = dmp.diff_main(old, new, False)
    # Make it more logical, don't care about minimal diff
    dmp.diff_cleanupSemantic(diff)
    return diff


def get_content_nodes(tree):
    for n in tree.childNodes:
        if n.nodeType in (dom.Node.TEXT_NODE,):
            yield n
        else:
            for n in get_content_nodes(n):
                yield n


def node_text(n):
    if n.nodeType is dom.Node.TEXT_NODE:
        return n.data
    return ''


def nodes_to_text(node_list):
    return ''.join([node_text(n) for n in node_list])


def split_node(node, length):
    if len(node_text(node)) <= length:
        return None
    return node.splitText(length)


def merge_diffs(diff_yours, diff_theirs):
    # align and split unchanged parts in both diffs
    diff_yours_merged = []
    diff_theirs_merged = []
    
    while True:
        yours = None
        theirs = None
        # advance to equal or deleted
        while diff_yours:
            yours = diff_yours.pop(0)
            if yours[0] != INSERT:
                break
            diff_yours_merged.append(yours)
            yours = None
    
        while diff_theirs:
            theirs = diff_theirs.pop(0)
            if theirs[0] != INSERT:
                break
            diff_theirs_merged.append(theirs)
            theirs = None

        if not yours or not theirs:
            break
        shortest = min(len(yours[1]), len(theirs[1]))
        diff_yours_merged.append((yours[0], yours[1][:shortest]))
        diff_theirs_merged.append((theirs[0], theirs[1][:shortest]))
        yours_unused = yours[1][shortest:]
        theirs_unused = theirs[1][shortest:]
        if yours_unused:
            diff_yours.insert(0, (yours[0], yours_unused))
        if theirs_unused:
            diff_theirs.insert(0, (theirs[0], theirs_unused))
    
    return diff_yours_merged, diff_theirs_merged


def align_diff(diff, content_before, content_after):
    # align diff to node boundaries across 2 doms, splitting nodes as necessary
    aligned_diff = []
    diff = diff[:]
    content_before = content_before[:]
    content_after = content_after[:]
    # stacks, yo
    while diff:
        d = diff.pop(0)
        d_text = d[1]
        if content_before:
            before = content_before.pop(0)
            before_text = node_text(before)
        if content_after:
            after = content_after.pop(0)
            after_text = node_text(after)
        if d[0] == diff_match_patch.DIFF_EQUAL:
            shortest = min(len(d_text), len(before_text), len(after_text))
            before_unused = split_node(before, shortest)
            after_unused = split_node(after, shortest)
            d_text_unused = d_text[shortest:]
            aligned_diff.append((diff_match_patch.DIFF_EQUAL, before, after))
        elif d[0] == diff_match_patch.DIFF_DELETE:
            shortest = min(len(d_text), len(before_text))
            before_unused = split_node(before, shortest)
            after_unused = after
            d_text_unused = d_text[shortest:]
            aligned_diff.append((diff_match_patch.DIFF_DELETE, before))
        else:  # DIFF_INSERT
            shortest = min(len(d_text), len(after_text))
            before_unused = before
            after_unused = split_node(after, shortest)
            d_text_unused = d_text[shortest:]
            aligned_diff.append((diff_match_patch.DIFF_INSERT, after))
        # push unspent content back on the stack
        if before_unused:
            content_before.insert(0, before_unused)
        if after_unused:
            content_after.insert(0, after_unused)
        if d_text_unused:
            diff.insert(0, (d[0], d_text_unused))
    return aligned_diff

def get_styles(content_node):
    styles = []
    node = content_node
    while node.parentNode and node.parentNode.parentNode:
        node = node.parentNode
        styles.append({'tag': node.nodeName, 'attributes': node.attributes})
    return styles

def merge_styles(yours, theirs):
    old_styles = get_styles(yours[1])
    your_styles = get_styles(yours[2])
    their_styles = get_styles(theirs[2])
    # should use a better diff that respects order, this shouldn't be that bad though
    old_tags = set([s['tag'] for s in old_styles])
    your_tags = set([s['tag'] for s in your_styles])
    their_tags = set([s['tag'] for s in their_styles])
    common = your_tags.intersection(their_tags)
    merged = your_tags.union(their_tags).difference(old_tags).union(common)
    theirs_added = their_tags.difference(your_tags)
    merged_styles = [style for style in their_styles if style['tag'] in theirs_added]
    merged_styles += [style for style in your_styles if style['tag'] in merged]
    return merged_styles


def construct_node(dom, styles):
    styles = styles[:]
    styles.reverse()
    root = None
    last = None
    for s in styles:
        n = dom.createElement(s['tag'])
        n.attributes = s['attributes']
        if not root:
            root = n
        if last:
            last.appendChild(n)
        last = n
    return root, n

def merge_html(yours, theirs, ancestor):
    tree_yours = parse_fragment(yours)
    content_yours = list(get_content_nodes(tree_yours))
    text_yours = nodes_to_text(content_yours)

    tree_theirs = parse_fragment(theirs)
    content_theirs = list(get_content_nodes(tree_theirs))
    text_theirs = nodes_to_text(content_theirs)
    
    tree_old = parse_fragment(ancestor)
    content_old = list(get_content_nodes(tree_old))
    text_old = nodes_to_text(content_old)
    
    diff_yours = diff_text(text_old, text_yours)
    diff_theirs = diff_text(text_old, text_theirs)

    diff_yours, diff_theirs = merge_diffs(diff_yours, diff_theirs)
    
    align_diff(diff_yours, content_old, content_yours)
    content_old = list(get_content_nodes(tree_old))
    diff_theirs_aligned = align_diff(diff_theirs, content_old, content_theirs)
    # align 'yours' again to propagate changes. ugly, but simple
    content_old = list(get_content_nodes(tree_old))
    content_yours = list(get_content_nodes(tree_yours))
    diff_yours_aligned = align_diff(diff_yours, content_old, content_yours)

    # merge content nodes
    merged_content = []
    while diff_theirs_aligned or diff_yours_aligned:
        theirs = diff_theirs_aligned and diff_theirs_aligned[0] or None
        yours = diff_yours_aligned and diff_yours_aligned[0] or None
        if yours and theirs and yours[0] in [EQUAL, DELETE] and theirs[0] in [EQUAL, DELETE]:
            diff_theirs_aligned.pop(0)
            diff_yours_aligned.pop(0)
            if yours[0] == DELETE or theirs[0] == DELETE:
                continue
        if yours and yours[0] == INSERT:
            diff_yours_aligned.pop(0)
        if theirs and theirs[0] == INSERT:
            diff_theirs_aligned.pop(0)
        merged_content.append({'yours': yours, 'theirs': theirs})

    # build tree, merge styles
    tree_merged = dom.minidom.Document()
    current_root = None
    current_node = None
    for piece in merged_content:
        yours = piece['yours']
        theirs = piece['theirs']
        content = None
        if yours and theirs:
            if yours[0] == INSERT:
                continue
            else:
                required_styles = merge_styles(yours, theirs)
                content = yours[1]
        if not yours:
            required_styles = get_styles(theirs[1])
            content = theirs[1]
        if not theirs:
            required_styles = get_styles(yours[1])
            content = yours[1]
        # put the content in the tree
        if not current_node:
            current_root, current_node = construct_node(tree_merged, required_styles)
        current_node.appendChild(content)
    return serialize(tree_merged)

