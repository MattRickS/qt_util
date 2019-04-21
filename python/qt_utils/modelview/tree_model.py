from collections import defaultdict
from itertools import groupby, count

from PySide2 import QtCore

from qt_utils.modelview import tree_node


class TreeModel(QtCore.QAbstractItemModel):
    """
    A model for displaying a tree of TreeNode items.

    Do not edit the node tree directly unless implementing the required signals.
    Convenience methods are provided for for adding/inserting nodes with the
    correct UI updates.
    """
    def __init__(self, root=None, parent=None):
        # type: (tree_node.TreeNode, QtCore.QObject) -> None
        super(TreeModel, self).__init__(parent)
        self._root = root or tree_node.TreeNode('root')

    @property
    def root(self):
        # type: () -> tree_node.TreeNode
        """ The root node of the tree """
        return self._root

    def clear(self):
        """ Removes all items from the tree """
        self.beginRemoveRows(QtCore.QModelIndex(), 0, self._root.child_count())
        self._root.clear()
        self.endRemoveRows()

    def index_for_node(self, node):
        # type: (tree_node.TreeNode) -> QtCore.QModelIndex
        """ Returns the QModelIndex for the node """
        index = QtCore.QModelIndex()
        # Ignore the root node, start from the first child
        for _node in node.hierarchy()[1:]:
            index = self.index(_node.row(), 0, index)
            if not index.isValid():
                raise ValueError('Node is not part of the tree: {}'.format(node))

        # Ensure the node is stored in the index
        if index.isValid() and index.internalPointer() != node:
            raise ValueError('Node is not part of the tree: {}'.format(node))

        return index

    def insert_nodes(self, parent_node, nodes, row=-1):
        # type: (tree_node.TreeNode, list[tree_node.TreeNode], int) -> bool
        """
        Inserts the nodes into the tree under the parent node.
        To add nodes, pass the child count of the parent node as the row.
        """
        # Ensure negative numbers are wrapped around to positive values
        if row < 0:
            row += parent_node.child_count()

        parent_index = self.index_for_node(parent_node)
        self.beginInsertRows(parent_index, row, row + len(nodes) - 1)
        for idx, node in enumerate(nodes):
            parent_node.insert_child(row + idx, node)
        self.endInsertRows()
        return True

    def remove_nodes(self, nodes):
        # type: (list[tree_node.TreeNode]) -> None
        """ Removes all the given nodes from the tree """
        # Group nodes to remove by their parent node
        mapping = defaultdict(list)
        for n in nodes:
            mapping[n.parent].append(n)

        # Iterate over the mapping to remove each group of nodes separately
        for parent, children in mapping.items():
            parent_index = self.index_for_node(parent)
            # The given nodes may not be sequential. Group them into sequential
            # indices and remove each batch in a separate begin/end context
            index_mapping = {child.row(): child for child in children}
            for _, grp in groupby(sorted(index_mapping), key=lambda x, y=count(): x - next(y)):
                indices = tuple(grp)
                start, end = indices[0], indices[-1]
                self.beginRemoveRows(parent_index, start, end)
                for i in range(end, start - 1, -1):
                    child = index_mapping[i]
                    parent.remove_node(child)
                self.endRemoveRows()

    def set_root_node(self, node):
        # type: (tree_node.TreeNode) -> None
        """ Replaces the entire tree model. Emits a full model reset. """
        self.beginResetModel()
        self._root = node
        self.endResetModel()

    # ======================================================================== #
    #  Subclassed
    # ======================================================================== #

    def columnCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        # type: (QtCore.QModelIndex, int) -> object
        if not index.isValid():
            return
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.name

    def flags(self, index):
        # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def hasChildren(self, parent):
        # type: (QtCore.QModelIndex) -> bool
        parent_node = parent.internalPointer() if parent.isValid() else self._root
        return parent_node.is_group()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        # type: (int, QtCore.Qt.Orientation, int) -> str
        if role == QtCore.Qt.DisplayRole:
            return 'name'

    def index(self, row, column, parent=QtCore.QModelIndex()):
        # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
        parent_node = parent.internalPointer() if parent.isValid() else self._root
        child = parent_node.child_by_index(row)
        return self.createIndex(row, column, child)

    def parent(self, child):
        # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
        node = child.internalPointer() if child.isValid() else self._root
        parent = node.parent
        return (QtCore.QModelIndex() if parent is None or parent == self._root else
                self.createIndex(parent.row(), 0, parent))

    def rowCount(self, parent=QtCore.QModelIndex()):
        # type: (QtCore.QModelIndex) -> int
        node = parent.internalPointer() if parent.isValid() else self._root
        return node.child_count()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        # type: (QtCore.QModelIndex, object, int) -> bool
        if not index.isValid():
            return False


if __name__ == '__main__':
    import sys

    from PySide2 import QtWidgets


    class Widget(QtWidgets.QWidget):
        def __init__(self, parent=None):
            # type: (QtWidgets.QWidget) -> None
            super(Widget, self).__init__(parent)

            root = tree_node.TreeNode('root')
            tree_node.TreeNode('one', parent=root)
            tree_node.TreeNode('two', parent=root)
            tree_node.TreeNode('three', parent=root)

            self.add_btn = QtWidgets.QPushButton('Add')
            self.sub_btn = QtWidgets.QPushButton('Remove')
            self.clear_btn = QtWidgets.QPushButton('Clear')
            self.reset_btn = QtWidgets.QPushButton('Reset')
            self.model = TreeModel(root=root)
            self.view = QtWidgets.QTreeView()
            self.view.setModel(self.model)
            self.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

            main_layout = QtWidgets.QVBoxLayout()
            main_layout.addWidget(self.add_btn)
            main_layout.addWidget(self.sub_btn)
            main_layout.addWidget(self.clear_btn)
            main_layout.addWidget(self.reset_btn)
            main_layout.addWidget(self.view)
            self.setLayout(main_layout)

            self.add_btn.clicked.connect(self.on_add_clicked)
            self.clear_btn.clicked.connect(self.model.clear)
            self.reset_btn.clicked.connect(self.reset)
            self.sub_btn.clicked.connect(self.on_sub_clicked)

        def reset(self):
            root = tree_node.TreeNode('root')
            tree_node.TreeNode('one', parent=root)
            tree_node.TreeNode('two', parent=root)
            tree_node.TreeNode('three', parent=root)
            self.model.set_root_node(root)

        def on_add_clicked(self):
            nodes = [index.internalPointer() for index in self.view.selectedIndexes()
                     if index.isValid()]
            for node in nodes:
                self.model.insert_nodes(
                    node,
                    [
                        tree_node.TreeNode('one'),
                        tree_node.TreeNode('two'),
                        tree_node.TreeNode('three'),
                    ],
                    row=node.child_count()
                )

        def on_sub_clicked(self):
            nodes = [index.internalPointer() for index in self.view.selectedIndexes()
                     if index.isValid()]
            self.model.remove_nodes(nodes)


    app = QtWidgets.QApplication(sys.argv)

    w = Widget()
    w.show()

    app.exec_()
    sys.exit()
