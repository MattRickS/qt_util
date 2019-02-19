class TreeNode(object):
    """
    Placeholder object which defines a name and may or may not contain an
    object from the source model. TreeNode's that do not contain an object
    are considered 'Groups', ie, they serve no purpose other than to contain
    other TreeNodes
    """
    def __init__(self, name, parent=None, source_row=None):
        # type: (str, TreeNode, int) -> None
        self._name = str(name)
        self._source_row = source_row
        self._children = []  # type: list[TreeNode]
        self._parent = None  # type: TreeNode

        if parent is not None:
            parent.add_child(self)

    def __repr__(self):
        return 'TreeNode({!r}, {}, {})'.format(self._name, self._parent, self._source_row)

    def __str__(self):
        return self.path

    @property
    def children(self):
        # type: () -> list[TreeNode]
        return self._children[:]

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def parent(self):
        # type: () -> TreeNode
        return self._parent

    @property
    def path(self):
        # type: () -> str
        return '.'.join(reversed([n.name for n in self.hierarchy()]))

    @property
    def source_row(self):
        """ The item for the source model that is being stored """
        return self._source_row

    def add_child(self, node):
        # type: (TreeNode) -> None
        node._parent = self
        self._children.append(node)

    def child_by_index(self, index):
        # type: (int) -> TreeNode
        return self._children[index]

    def child_by_name(self, name):
        # type: (str) -> TreeNode
        for child in self._children:
            if child.name == name:
                return child

    def child_count(self):
        # type: () -> int
        return len(self._children)

    def clear(self):
        self._children = []

    def descendants(self):
        # type: () -> list[TreeNode]
        """ Iterator of all descendants """
        for child in self._children:
            yield child
            yield from child.descendants()

    def has_children(self):
        # type: () -> bool
        return bool(self._children)

    def hierarchy(self):
        # type: () -> list[TreeNode]
        """ Iterator from self to the root node """
        node = self
        while node is not None:
            yield node
            node = node.parent

    def is_group(self):
        # type: () -> bool
        return self._source_row is None

    def is_leaf(self):
        # type: () -> bool
        return len(self._children) == 0

    def row(self):
        # type: () -> int
        return 0 if self._parent is None else self._parent._children.index(self)

    def to_string(self, level=0):
        # type: (int) -> str
        s = '. ' * level + '{!r} {!r}'.format(self._name, self._source_row) + '\n'
        for child in self._children:
            s += child.to_string(level + 1)
        return s
