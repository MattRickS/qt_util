import contextlib

from PySide2 import QtCore, QtGui, QtWidgets


class ObjectDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        value = index.data(TreeObjectDisplay.ValueRole)
        if isinstance(value, bool):
            return QtWidgets.QCheckBox(parent)
        elif isinstance(value, int):
            return QtWidgets.QSpinBox(parent)
        elif isinstance(value, float):
            return QtWidgets.QDoubleSpinBox(parent)
        elif isinstance(value, str) or value is None:
            return QtWidgets.QLineEdit(parent)
        else:
            return super(ObjectDelegate, self).createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        # type: (QtWidgets.QWidget, QtCore.QModelIndex) -> None
        value = index.data(TreeObjectDisplay.ValueRole)
        if isinstance(editor, QtWidgets.QCheckBox):
            editor.setChecked(value)
        elif isinstance(editor, QtWidgets.QAbstractSpinBox):
            editor.setValue(value)
        elif isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(value)
        else:
            super(ObjectDelegate, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        # type: (QtWidgets.QWidget, QtCore.QAbstractItemModel, QtCore.QModelIndex) -> None
        if isinstance(editor, QtWidgets.QCheckBox):
            value = editor.isChecked()
        elif isinstance(editor, QtWidgets.QAbstractSpinBox):
            value = editor.value()
        elif isinstance(editor, QtWidgets.QLineEdit):
            value = editor.text()
        else:
            super(ObjectDelegate, self).setModelData(editor, model, index)
            return

        super(ObjectDelegate, self).setModelData(editor, model, index)
        model.setData(index, value, TreeObjectDisplay.ValueRole)
        
    def paint(self, painter, option, index):
        tree_widget = self.parent()
        item = tree_widget.itemFromIndex(index)
        if tree_widget.is_container_item(item):
            paired = tree_widget.paired_container_item(item)
            if paired.isSelected():
                option.state |= QtWidgets.QStyle.State_Selected
        super(ObjectDelegate, self).paint(painter, option, index)


class TreeObjectDisplay(QtWidgets.QTreeWidget):
    """
    Capable of displaying arbitrary python datasets in a tree hierarchy,
    maintaining ordering and nesting. Data is coloured by type, and iterables
    are displayed with enclosing literals.

    The chain of __getitem__ calls that would reach an item from the source
    object can be retrieved using path_to_item().

    The tree can be made editable, with a default editor supplied for each base
    datatype (bool, float, int, string). None types are treated as strings.
    """

    ContainerOpenItemType = QtWidgets.QTreeWidgetItem.UserType + 1
    ContainerCloseItemType = QtWidgets.QTreeWidgetItem.UserType + 2
    ValueItemType = QtWidgets.QTreeWidgetItem.UserType + 3
    KeyItemType = QtWidgets.QTreeWidgetItem.UserType + 4

    ValueRole = QtCore.Qt.UserRole + 1
    GetItemRole = QtCore.Qt.UserRole + 2
    ContainerTypeRole = QtCore.Qt.UserRole + 3

    @classmethod
    def from_object(cls, obj, editable=False, parent=None):
        """
        Args:
            obj (object): Python object to construct the display for
            editable (:obj:`bool`, optional): Whether or not the value items
                can be edited.
            parent (:obj:`QtWidgets.QWidget`, optional):

        Returns:
            TreeObjectDisplay
        """
        widget = cls(editable=editable, parent=parent)
        widget.add_object(obj)
        return widget

    @classmethod
    def show_object(cls, obj, editable=False, expanded=True, parent=None):
        """
        Convenience method for displaying the object immediately

        Args:
            obj (object): Python object to construct the display for
            editable (:obj:`bool`, optional): Whether or not the value items
                can be edited.
            expanded (:obj:`bool`, optional): Whether or not to recursively
                expand the display
            parent (:obj:`QtWidgets.QWidget`, optional):

        Returns:
            TreeObjectDisplay
        """
        widget = cls.from_object(obj, editable=editable, parent=parent)
        if expanded:
            widget.expandAll()
        widget.show()
        return widget

    def __init__(self, parent=None, editable=False):
        """
        Args:
            parent (:obj:`QtWidgets.QWidget`, optional):
        """
        super(TreeObjectDisplay, self).__init__(parent)
        self.setItemDelegate(ObjectDelegate(self))
        self.header().hide()

        self._editable = editable
        self.colours = {
            int: QtGui.QColor("cyan"),
            float: QtGui.QColor("cyan"),
            str: QtGui.QColor("green"),
            bool: QtGui.QColor("orange"),
            type(None): QtGui.QColor("red"),
        }
        self.symbols = {
            tuple: ("(", ")"),
            list: ("[", "]"),
            set: ("{", "}"),
            dict: ("{", "}"),
        }

        self.currentItemChanged.connect(self.on_item_selection_changed)

    @contextlib.contextmanager
    def container_creation(self, container_type, parent=None, previous=None):
        """
        Context manager for creating container items. Context yields a list of
        items that will initially contain the start item, and will append the
        closing item upon completion. Literals for the container type are
        extracted from the symbols mapping using their corresponding type.

        Args:
            container_type (Type):
            parent (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                create the object under. If not given, defaults to root.
            previous (:obj:`QtWidgets.QTreeWidgetItem`, optional=True): Item to
                place the new item after.
        """
        start_symbol, end_symbol = self.symbols[container_type]
        start_item = self.add_item(
            start_symbol,
            parent=parent,
            previous=previous,
            item_type=self.ContainerOpenItemType,
        )
        start_item.setData(0, self.ContainerTypeRole, container_type)
        items = [start_item]

        yield items

        end_item = self.add_item(
            end_symbol,
            parent=parent,
            previous=start_item,
            item_type=self.ContainerCloseItemType,
        )
        end_item.setData(0, self.ContainerTypeRole, container_type)
        items.append(end_item)

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
        dict_type = type(dct)

        with self.container_creation(
            dict_type, parent=parent, previous=previous
        ) as items:
            start_item = items[0]
            last_item = None
            for key, value in dct.items():
                last_item = self.add_item(
                    key,
                    parent=start_item,
                    previous=last_item,
                    item_type=self.KeyItemType,
                )
                last_item.setData(0, self.GetItemRole, key)
                self.add_object(value, parent=last_item)

        return items

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
        iterable_type = type(iterable)

        with self.container_creation(
            iterable_type, parent=parent, previous=previous
        ) as items:
            start_item = items[0]
            last_item = None
            for i, val in enumerate(iterable):
                first_item, final_item = self.add_object(
                    val, parent=start_item, previous=last_item
                )
                last_item = final_item or first_item
                last_item.setData(0, self.GetItemRole, i)

        return items

    def add_item(self, value, parent=None, previous=None, item_type=ValueItemType):
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
        if item_type == self.ValueItemType:
            item.setData(0, self.ValueRole, value)
            if self.is_editable():
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        if item_type in (self.ValueItemType, self.KeyItemType):
            value_type = type(value)
            colour = self.colours.get(value_type)
            if colour is not None:
                item.setData(0, QtCore.Qt.ForegroundRole, colour)

        return item

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
            items = self.add_dict(obj, parent=parent, previous=previous)
        elif isinstance(obj, (list, tuple, set)):
            items = self.add_iterable(obj, parent=parent, previous=previous)
        else:
            item = self.add_item(obj, parent=parent, previous=previous)
            items = (item, None)
        return items

    def is_container_item(self, item):
        """
        Args:
            item (QtWidgets.QTreeWidgetItem): Item from the tree

        Returns:
            bool: Whether or not the item represents a container item rather
                than an actual value
        """
        return item.type() in (self.ContainerOpenItemType, self.ContainerCloseItemType)

    def is_editable(self):
        """
        Returns:
            bool: Whether or not the value items are editable
        """
        return self._editable

    def item_from_path(self, path, parent_item):
        """
        Raises:
            TypeError: If parent_item is not a container, or container type is
                unknown
            ValueError: If any of the provided path items are invalid or do not
                resolve to an item.

        Args:
            path (list): List of __getitem__ values to walk through
            parent_item (QtWidgets.QTreeWidgetItem): Item to start walking from.
                Must be a container item.

        Returns:
            QtWidgets.QTreeWidgetItem: Item the path resolves to
        """
        parent_item = parent_item or self.topLevelItem(0)
        if parent_item is not None and not self.is_container_item(parent_item):
            raise TypeError("Parent item must be a container type")

        container_type = parent_item.data(0, self.ContainerTypeRole)
        value = path.pop(0)
        if container_type in (list, set, tuple):
            if not isinstance(value, int):
                raise ValueError(
                    "Invalid __getitem__ for list type, must be int, got {}".format(
                        value
                    )
                )
            if value < 0 or value > parent_item.childCount():
                raise ValueError(
                    "Invalid index {} for parent item {}".format(value, parent_item)
                )
            value_item = parent_item.child(value)
        elif container_type == dict:
            for row in range(parent_item.childCount()):
                key_item = parent_item.child(row)
                getitem_value = key_item.data(0, self.GetItemRole)
                if getitem_value == value:
                    value_item = key_item.child(0)
                    break
            else:
                raise ValueError(
                    "No key matches {} for parent item {}".format(value, parent_item)
                )
        else:
            raise TypeError("Unknown parent item type: {}".format(parent_item))

        if not path:
            return value_item

        return self.item_from_path(path, value_item)

    def object_from_item(self, item, key_to_value=True):
        """
        Walks through an item's hierarchy and constructs the python object
        represented beneath it. Warning: Key items will return just the key
        value

        Raises:
            TypeError: If item is a container and type is unknown

        Args:
            item (QtWidgets.QTreeWidgetItem): Item to begin converting from
            key_to_value (:obj:`bool`, optional): If True (default), items
                representing a dictionary key will return their value from the
                dictionary. If False, they will return just the key's value.

        Returns:
            object: Object recursively constructed from the item and it's
                descendants.
        """
        if key_to_value and item.type() == self.KeyItemType:
            item = item.child(0)

        if self.is_container_item(item):
            container_type = item.data(0, self.ContainerTypeRole)
            if container_type == dict:
                data = {}
                for row in range(item.childCount()):
                    key_item = item.child(row)
                    value_item = key_item.child(0)
                    key = key_item.data(0, self.GetItemRole)
                    value = self.object_from_item(value_item)
                    data[key] = value
            elif container_type in (list, tuple, set):
                values = (
                    self.object_from_item(item.child(row))
                    for row in range(item.childCount())
                )
                data = container_type(values)
            else:
                raise TypeError(
                    "Unknown container type {} for item {}".format(container_type, item)
                )
        else:
            data = item.data(0, self.ValueRole)
        return data

    def objects(self):
        """
        Returns:
            list[object]: List of all top level items converted to objects
        """
        return [
            self.object_from_item(self.topLevelItem(row))
            for row in range(self.topLevelItemCount())
        ]

    def paired_container_item(self, item):
        """
        Raises:
            TypeError: If given item is not a container item

        Args:
            item (QtWidgets.QTreeWidgetItem):

        Returns:
            QtWidgets.QTreeWidgetItem: Paired container open/close item
        """
        if not self.is_container_item(item):
            raise TypeError("Item is not a container item: {}".format(item))

        parent = item.parent()
        if parent is None:
            parent = self.invisibleRootItem()

        row = parent.indexOfChild(item)
        if item.type() == TreeObjectDisplay.ContainerOpenItemType:
            row += 1
        else:
            row -= 1

        sibling_item = parent.child(row)
        return sibling_item

    def path_from_item(self, item):
        """
        Examples:
            >>> obj = {"key_1": {"key_2": [1, 2, 3]}}
            >>> widget = TreeObjectDisplay.from_obj(obj)
            >>> #             {               key_1   {         key_2    [        2
            >>> item = widget.topLevelItem(0).child(0).child(0).child(0).child(0).child(1)
            >>> widget.path_from_item(item)
            # ["key_1", "key_2", 1]

        Args:
            item (QtWidgets.QTreeWidgetItem):

        Returns:
            list: List of __getitem__ calls required to access the item from the
                source object
        """
        path = []
        while item is not None:
            get_item = item.data(0, self.GetItemRole)
            # None is a valid dictionary key
            if get_item is not None or item.type() == self.KeyItemType:
                path.append(get_item)
            item = item.parent()
        return path[::-1]

    def set_editable(self, editable):
        """
        Args:
            editable (bool): Whether or not the value items should be editable
        """
        self._editable = bool(editable)
        flags = (QtWidgets.QTreeWidgetItemIterator.NotEditable if editable else QtWidgets.QTreeWidgetItemIterator.Editable)
        iterator = QtWidgets.QTreeWidgetItemIterator(self, flags)
        while iterator.value():
            item = iterator.value()

            if item.type() == self.ValueItemType:
                item_flags = item.flags()
                if editable:
                    item_flags |= QtCore.Qt.ItemIsEditable
                else:
                    item_flags &= ~QtCore.Qt.ItemIsEditable
                item.setFlags(item_flags)

            iterator += 1

    def on_item_selection_changed(self, current, previous):
        """
        Refreshes paired container items simultaneously to allow for selection
        highlighting

        Args:
            current (QtWidgets.QTreeWidgetItem):
            previous (QtWidgets.QTreeWidgetItem):
        """
        for item in (current, previous):
            if item is None or not self.is_container_item(item):
                continue

            paired = self.paired_container_item(item)
            if paired is None:
                continue

            index = self.indexFromItem(paired)
            self.model().dataChanged.emit(index, index)


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

    widget = TreeObjectDisplay.show_object(obj, editable=True)
    print(widget.objects())

    def debug():
        for item in widget.selectedItems():
            print("=" * 50)
            print(item)
            path = widget.path_from_item(item)
            print(path)
            print(widget.object_from_item(item))
            if path:
                solved_item = widget.item_from_path(path, widget.topLevelItem(0))
                print(solved_item)
                print(widget.object_from_item(item))
                print(widget.path_from_item(solved_item))

    widget.itemSelectionChanged.connect(debug)

    app.exec_()
    sys.exit()
