from typing import Iterator


class TreeNode(object):
    """
    Basic node class for providing a two way parent-child hierarchy.
    TreeNode's are represented by a name, and may or may not contain a custom
    object accessed via `internal_item`
    """
    def __init__(self, name, internal_item=None, parent=None):
        # type: (str, object, TreeNode) -> None
        self.name = str(name)
        self.internal_item = internal_item
        self._children = []
        self._parent = None  # type: TreeNode

        if parent is not None:
            parent.add_child(self)

    def __repr__(self):
        return 'TreeNode({!r}, internal_item={!r}, parent={!r})'.format(
            self.name, self.internal_item, self._parent)

    def __str__(self):
        return self.path

    @property
    def children(self):
        # type: () -> list[TreeNode]
        """ Returns a copy of the list of child nodes """
        return self._children[:]

    @property
    def parent(self):
        # type: () -> TreeNode
        """ The parent node or None if this is the root node """
        return self._parent

    @property
    def path(self):
        # type: () -> str
        """ Dot joined string for all nodes from root to the current node """
        return '.'.join((n.name for n in self.hierarchy()))

    def add_child(self, node):
        # type: (TreeNode) -> None
        """ Adds a child node. This modifies the node's parent. """
        node._parent = self
        self._children.append(node)

    def ancestors(self):
        # type: () -> Iterator[TreeNode]
        """ Iterator of all parent nodes to root """
        parent = self.parent
        while parent:
            yield parent
            parent = parent.parent

    def child_by_index(self, index):
        # type: (int) -> TreeNode
        """ Retrieves the child at the given index """
        return self._children[index]

    def child_by_name(self, name):
        # type: (str) -> TreeNode
        """ Retrieves the first child node with a matching name """
        for child in self._children:
            if child.name == name:
                return child

    def child_count(self):
        # type: () -> int
        """ Number of child nodes """
        return len(self._children)

    def clear(self):
        """ Removes all child nodes """
        self._children = []

    def descendants(self):
        # type: () -> Iterator[TreeNode]
        """ Iterator of all descendants """
        for child in self._children:
            yield child
            for grandchild in child.descendants():
                yield grandchild

    def has_child(self, child):
        # type: (TreeNode) -> bool
        """ Returns a boolean for whether the given node is a child or not """
        return child in self._children

    def hierarchy(self):
        # type: () -> list[TreeNode]
        """ Returns all nodes in the hierarchy from root node to self """
        return list(self.ancestors())[::-1] + [self]

    def insert_child(self, index, child):
        # type: (int, TreeNode) -> None
        """ Inserts a child node at the given index """
        self._children.insert(index, child)
        child._parent = self

    def is_group(self):
        # type: () -> bool
        """ Whether or not the node contains other nodes """
        return bool(self._children)

    def is_leaf(self):
        # type: () -> bool
        """ Whether or not the node is at the end of the tree """
        return not bool(self._children)

    def remove_node(self, node):
        # type: (TreeNode) -> None
        """ Removes the child node. This modifies the node's parent. """
        self._children.remove(node)
        node._parent = None

    def row(self):
        # type: () -> int
        """ The node's index within it's parent's children """
        return 0 if self._parent is None else self._parent._children.index(self)

    def to_string(self, level=0):
        # type: (int) -> str
        """ Returns a string representing the node's sub-hierarchy """
        s = '. ' * level + '{!r} {!r}'.format(self.name, self.internal_item) + '\n'
        for child in self._children:
            s += child.to_string(level + 1)
        return s
