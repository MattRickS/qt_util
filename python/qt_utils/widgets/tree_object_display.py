from PySide2 import QtCore, QtGui, QtWidgets


class TreeObjectDisplay(QtWidgets.QTreeWidget):
    """
    Capable of displaying arbitrary python datasets in a tree hierarchy,
    maintaining ordering and nesting. Data is coloured by type, and iterables
    are displayed with enclosing literals.

    The chain of __getitem__ calls that would reach an item from the source
    object can be retrieved using path_to_item().
    """
    # TODO: Change to CONTAINER_TYPE and store the class in a ContainerTypeRole
    DICT_ITEM_TYPE = QtWidgets.QTreeWidgetItem.UserType + 1
    LIST_ITEM_TYPE = QtWidgets.QTreeWidgetItem.UserType + 2
    VALUE_ITEM_TYPE = QtWidgets.QTreeWidgetItem.UserType + 3
    KEY_ITEM_TYPE = QtWidgets.QTreeWidgetItem.UserType + 4

    ValueRole = QtCore.Qt.UserRole + 1
    GetItemRole = QtCore.Qt.UserRole + 2

    @classmethod
    def from_object(cls, obj, parent=None):
        """
        Args:
            obj (object): Python object to construct the display for
            parent (:obj:`QtWidgets.QWidget`, optional):

        Returns:
            TreeObjectDisplay
        """
        widget = cls(parent)
        widget.add_object(obj)
        return widget

    @classmethod
    def show_object(cls, obj, expanded=True, parent=None):
        """
        Convenience method for displaying the object immediately

        Args:
            obj (object): Python object to construct the display for
            expanded (:obj:`bool`, optional): Whether or not to recursively
                expand the display
            parent (:obj:`QtWidgets.QWidget`, optional):

        Returns:
            TreeObjectDisplay
        """
        widget = cls.from_object(obj, parent=parent)
        if expanded:
            widget.expandAll()
        widget.show()
        return widget

    def __init__(self, parent=None):
        """
        Args:
            parent (:obj:`QtWidgets.QWidget`, optional):
        """
        super(TreeObjectDisplay, self).__init__(parent)
        self.header().hide()
        self.colours = {
            int: QtGui.QColor("cyan"),
            float: QtGui.QColor("cyan"),
            str: QtGui.QColor("green"),
            bool: QtGui.QColor("orange"),
            type(None): QtGui.QColor("red")
        }
        self.symbols = {
            tuple: ("(", ")"),
            list: ("[", "]"),
            set: ("{", "}"),
            dict: ("{", "}"),
        }

    def path_to_item(self, item):
        """
        Examples:
            >>> obj = {"key_1": {"key_2": [1, 2, 3]}}
            >>> widget = TreeObjectDisplay.from_obj(obj)
            >>> #             {               key_1   {         key_2    [        2
            >>> item = widget.topLevelItem(0).child(0).child(0).child(0).child(0).child(1)
            >>> widget.path_to_item(item)
            # ["key_1", "key_2", 1]

        Args:
            item (QtWidgets.QTreeWidgetItem):

        Returns:
            list: List of __getitem__ calls required to access the item from the
                source object
        """
        path = []
        while item is not None:
            if item is not None:
                get_item = item.data(0, self.GetItemRole)
                # None is a valid dictionary key
                if get_item is not None or item.type() == self.KEY_ITEM_TYPE:
                    path.append(get_item)
            item = item.parent()
        return path[::-1]

    def add_object(self, obj, parent=None, previous=None):
        """
        Determines the object type and builds the corresponding tree item.

        Args:
            obj (object): Object to add
            parent (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                create the object under. If not given, defaults to root.
            previous (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                place the new item after.

        Returns:
            QtWidgets.QTreeWidgetItem: Last created item
        """
        if isinstance(obj, dict):
            item = self.add_dict(obj, parent=parent, previous=previous)
        elif isinstance(obj, (list, tuple, set)):
            item = self.add_iterable(obj, parent=parent, previous=previous)
        else:
            item = self.add_item(obj, parent=parent, previous=previous)
        return item

    def add_dict(self, dct, parent=None, previous=None):
        """
        Args:
            dct (dict):
            parent (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                create the object under. If not given, defaults to root.
            previous (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                place the new item after.

        Returns:
            QtWidgets.QTreeWidgetItem: Item for the closing literal
        """
        start_symbol, end_symbol = self.symbols[dict]
        start_item = self.add_item(
            start_symbol, parent=parent, previous=previous, item_type=self.DICT_ITEM_TYPE
        )

        last_item = None
        for key, value in dct.items():
            last_item = self.add_item(
                key, parent=start_item, previous=last_item, item_type=self.KEY_ITEM_TYPE
            )
            last_item.setData(0, self.GetItemRole, key)
            self.add_object(value, parent=last_item)

        end_item = self.add_item(
            end_symbol, parent=parent, previous=start_item, item_type=self.DICT_ITEM_TYPE
        )
        return end_item

    def add_iterable(self, iterable, parent=None, previous=None):
        """
        Creates an iterable array inside two enclosing items. The literal used
        for the closing items is taken from symbols using the iterable type.

        Args:
            iterable (Iterable):
            parent (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                create the object under. If not given, defaults to root.
            previous (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                place the new item after.

        Returns:
            QtWidgets.QTreeWidgetItem: Item for the closing literal
        """
        start_symbol, end_symbol = self.symbols[type(iterable)]
        start_item = self.add_item(
            start_symbol, parent=parent, previous=previous, item_type=self.LIST_ITEM_TYPE
        )

        last_item = None
        for i, val in enumerate(iterable):
            last_item = self.add_object(val, parent=start_item, previous=last_item)
            last_item.setData(0, self.GetItemRole, i)

        end_item = self.add_item(
            end_symbol, parent=parent, previous=start_item, item_type=self.LIST_ITEM_TYPE
        )
        return end_item

    def add_item(self, value, parent=None, previous=None, item_type=VALUE_ITEM_TYPE):
        """
        Adds a string representation of a value as a single item to the tree.
        The value object is stored in the ValueRole as long as the item_type is
        the default value type. Custom types must handle their own storage
        requirements.

        Key and Value Item Types have their foreground role set using the
        corresponding type from the colours mapping.

        Args:
            value (object):
            parent (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                create the object under. If not given, defaults to root.
            previous (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                place the new item after.
            item_type (:obj:`QtWidgets.QTreeWidgetItem.ItemType`): ItemType to
                create the widget as. The ValueRole for the item is only stored
                if the item type is the default

        Returns:
            QtWidgets.QTreeWidgetItem: Created item
        """
        item = QtWidgets.QTreeWidgetItem(parent or self, previous, item_type)
        item.setText(0, str(value))
        if item_type == self.VALUE_ITEM_TYPE:
            item.setData(0, self.ValueRole, value)
        if item_type in (self.VALUE_ITEM_TYPE, self.KEY_ITEM_TYPE):
            try:
                value_type = type(value)
            except Exception:
                pass
            else:
                colour = self.colours.get(value_type)
                if colour is not None:
                    item.setData(0, QtCore.Qt.ForegroundRole, colour)

        return item


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    obj = {
        "contents": ["|root|node_{}".format(i) for i in range(10)],
        "something else": {None: {"grandchildren": [i for i in range(10, 20)]}},
        1: 5.0,
        "nested_lists": [
            [["a", "b", "c"], (1, 2), {4, 5, 6}, "not a list", {"key": "value"}],
            1,
            True,
            [1, 2, 3, 4],
            None,
        ],
    }

    widget = TreeObjectDisplay.show_object(obj)

    def debug():
        for item in widget.selectedItems():
            print("="*50)
            path = widget.path_to_item(item)
            print(path)
            # print(widget.item_to_object(item))
            # if path:
            #     solved_item = widget.item_for_path(path, widget.topLevelItem(0))
            #     print(solved_item)
            #     print(widget.path_to_item(solved_item))

    widget.itemSelectionChanged.connect(debug)

    app.exec_()
    sys.exit()
