from PySide2 import QtCore

from qt_utils.tree_node import TreeNode


class GroupProxyModel(QtCore.QAbstractProxyModel):
    """
    Proxy model which allows grouping of child indexes into a tree view based
    on a user defined method. The method must take the source index, and return
    a value or ordered iterable of values to group by.

    The model is read-only and does not implement any behaviours for modifying
    the graph or the source data.

    Example:
        # Assuming a model of 4 items: ['one', 'two', 'one', 'two']
        def group_method(index):
            return index.data(), index.row()

        model = Model()
        proxy = GroupProxyModel(group_method)
        proxy.setSourceModel(model)
        view = QtWidgets.QTreeView()
        view.setModel(proxy)
        view.show()

        ## Resulting tree view:
        # one
        # . 0
        # . . one
        # . 2
        # . . one
        # two
        # . 1
        # . . two
        # . 3
        # . . two

    Warning:
        The source model must be flat (ie, not a tree)
    """

    def __init__(self, group_method=None, node_class=TreeNode, parent=None):
        # type: (function, type) -> None
        super(GroupProxyModel, self).__init__(parent)
        if node_class is not None and TreeNode not in node_class.mro():
            raise ValueError('Custom Node class must inherit from TreeNode')
        self._node_class = node_class  # type: type
        self._root = self._node_class('root')
        self._group_method = group_method

    @property
    def root_node(self):
        # type: () -> TreeNode
        """ Invisible root node of the tree """
        return self._root

    def get_groups(self, index):
        # type: (QtCore.QModelIndex) -> list[str]
        """ Gets list of ordered groups based on the SOURCE model's index """
        if not index.isValid() or not self._group_method:
            return []
        values = self._group_method(index)
        values = (values,) if not hasattr(values, '__iter__') else values
        return list(map(str, values))

    def is_group_index(self, proxy_index):
        # type: (QtCore.QModelIndex) -> bool
        if not proxy_index.isValid():
            return False
        node = proxy_index.internalPointer()
        return isinstance(node, TreeNode) and node.is_group()

    def rebuild_tree(self):
        # type: () -> None
        """ Forces a rebuild of the tree using the last assigned method """
        self.beginResetModel()
        # Clear the existing tree first
        self._root.clear()

        # If no model is set, exit with an empty tree
        source_model = self.sourceModel()
        if source_model is None:
            return

        # Build the grouping for each source index
        for row in range(source_model.rowCount()):
            index = source_model.index(row, 0)
            if not index.isValid():
                continue
            groups = self.get_groups(index)
            # Walk the tree and create any missing groups
            current_node = self._root
            for grp in groups:
                current_node = (current_node.child_by_name(grp) or
                                self._create_node(grp, current_node))
            # Create the node that wraps the source model item
            self._create_node(index.data(QtCore.Qt.DisplayRole),
                              current_node,
                              source_row=row)

        self.endResetModel()

    def set_group_method(self, func):
        # type: (function|None) -> None
        """ Rebuilds the tree using the given method on each source index """
        self._group_method = func
        self.rebuild_tree()

    def ungroup(self):
        """ Removes any currently applied grouping method """
        self.set_group_method(None)

    def _create_node(self, name, parent, source_row=None):
        # type: (str, TreeNode, int) -> TreeNode
        """
        Creates a node on the tree. Only used internally by rebuild_tree,
        exists only so that subclasses can override behaviour.
        """
        return self._node_class(name, parent, source_row)

    # ======================================================================== #
    #                               SUBCLASSED                                 #
    # ======================================================================== #

    def buddy(self, index):
        return index

    def columnCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        src_index = self.mapToSource(parent)
        return self.sourceModel().columnCount(src_index)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        # type: (QtCore.QModelIndex, int) -> object
        if not index.isValid():
            return
        node = index.internalPointer()

        # Wrapped objects should display their data as normal
        if not node.is_group():
            return super(GroupProxyModel, self).data(index, role)

        # 'Group' nodes only display their group name on the first column
        if index.column() == 0 and role == QtCore.Qt.DisplayRole:
            return node.name

    def flags(self, index):
        # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
        # 'Group' nodes should use a default set of flags
        if self.is_group_index(index):
            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            return flags
        # Otherwise use the source behaviour
        src_index = self.mapToSource(index)
        src_flags = self.sourceModel().flags(src_index)
        return src_flags

    def hasChildren(self, proxy_index):
        # type: (QtCore.QModelIndex) -> bool
        # Empty index refers to the root node
        if not proxy_index.isValid():
            return self._root.has_children()
        # Parent child relationships only exist for the first column. Note that
        # invalid indexes refer to the root, so must be evaluated first
        elif proxy_index.column() != 0:
            return False
        else:
            node = proxy_index.internalPointer()
            return node.has_children()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        # type: (int, QtCore.Qt.Orientation, int) -> str
        # Virtual method: Must be implemented
        return self.sourceModel().headerData(section, orientation, role)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
        node = parent.internalPointer() if parent.isValid() else self._root
        child = node.child_by_index(row)
        return self.createIndex(row, column, child)

    def mapFromSource(self, source_index):
        # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
        # Guess what, empty source indexes are still empty in proxy!
        if not source_index.isValid():
            return QtCore.QModelIndex()

        # Get the correct group order for the source index, and walk to retrieve
        # the internal node used for the index
        groups = self.get_groups(source_index)
        current_node = self._root
        while groups:
            grp = groups.pop(0)
            current_node = current_node.child_by_name(grp)

        # Create a new index from the node's row, storing the TreeNode
        return self.createIndex(current_node.row(), source_index.column(), current_node)

    def mapToSource(self, proxy_index):
        # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
        # Empty indexes are always empty in both models
        if not proxy_index.isValid() or self.is_group_index(proxy_index):
            return QtCore.QModelIndex()

        # Walk through all source indexes til we find the one who's internal
        # object matches the node's
        node = proxy_index.internalPointer()
        source_model = self.sourceModel()
        src_index = source_model.index(node.source_row, proxy_index.column())
        return src_index

    def parent(self, child):
        # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
        # Unknown child gets an empty parent
        if not child.isValid():
            return QtCore.QModelIndex()

        # No parent index for the root or above
        node = child.internalPointer()
        parent_node = node.parent
        if parent_node is None or parent_node == self._root:
            return QtCore.QModelIndex()

        # Otherwise create the index for the node. Note, parent-child
        # relationships only exist for the first column
        return self.createIndex(parent_node.row(), 0, parent_node)

    def resetInternalData(self):
        # This method is only used for custom behaviour -- simply rebuild the
        # tree whenever the source model is reset
        super(GroupProxyModel, self).resetInternalData()
        self.rebuild_tree()

    def rowCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        # Invalid index refers to the root, otherwise get the internal node
        # Return the node's number of children
        node = parent.internalPointer() if parent.isValid() else self._root
        return node.child_count()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        # type: (QtCore.QModelIndex, object, int) -> bool
        src_index = self.mapToSource(index)
        return self.sourceModel().setData(src_index, value, role)

    def setSourceModel(self, model):
        # type: (QtCore.QAbstractItemModel) -> None
        current_source = self.sourceModel()
        if current_source is not None:
            current_source.modelReset.disconnect(self.resetInternalData)

        if model is not None:
            model.modelReset.connect(self.resetInternalData)

        super(GroupProxyModel, self).setSourceModel(model)
        self.resetInternalData()


if __name__ == '__main__':
    import sys
    from PySide2 import QtCore, QtGui, QtWidgets

    app = QtWidgets.QApplication(sys.argv)


    class Model(QtCore.QAbstractItemModel):
        def __init__(self, data=None, parent=None):
            super(Model, self).__init__(parent)
            self._data = data or []

        def set_data(self, data):
            self.beginResetModel()
            self._data = data or []
            self.endResetModel()

        def data(self, index, role=QtCore.Qt.DisplayRole):
            # type: (QtCore.QModelIndex, int) -> object
            if not index.isValid():
                return
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                return self._data[index.row()]

        def columnCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return 3

        def flags(self, index):
            # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

        def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
            # type: (int, QtCore.Qt.Orientation, int) -> str
            if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
                return 'header{}'.format(section)

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column, self._data[row])

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self._data)

        def setData(self, index, value, role=QtCore.Qt.EditRole):
            # type: (QtCore.QModelIndex, object, int) -> bool
            if not index.isValid() or role != QtCore.Qt.EditRole:
                return False
            self._data[index.row()] = str(value)
            self.dataChanged.emit(index, index)
            return True


    def reset(model):
        print('Resetting:', model)

    def group(index):
        if not index.isValid():
            return []
        obj = index.internalPointer()
        return int(obj) // 3

    m = Model([str(i) for i in range(10)])
    m.modelReset.connect(lambda: reset('model'))
    p = GroupProxyModel(group)
    p.modelReset.connect(lambda: reset('proxy'))
    p.setSourceModel(m)
    v = QtWidgets.QTreeView()
    v.setModel(p)
    v.show()

    app.exec_()
    sys.exit()
