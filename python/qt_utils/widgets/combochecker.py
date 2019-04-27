from PySide2 import QtCore, QtGui, QtWidgets


class ComboChecker(QtWidgets.QComboBox):
    itemStateChanged = QtCore.Signal(QtGui.QStandardItem)

    def __init__(self, parent=None):
        super(ComboChecker, self).__init__(parent)
        self.view().pressed.connect(self.onItemPressed)
        self._changed = False
        self._default_string = 'Select Items...'
        self._selection_string = self._default_string

    def checkedItems(self):
        """
        Returns:
            list[QtGui.QStandardItem]: List of all checked items in the model
        """
        items = []
        for row in range(self.model().rowCount()):
            item = self.model().item(row, self.modelColumn())
            if item.checkState() == QtCore.Qt.Checked:
                items.append(item)
        return items

    def checkedText(self):
        """
        Returns:
            list[str]: List of all checked text in the model
        """
        return [item.text() for item in self.checkedItems()]

    def itemChecked(self, index):
        """
        Args:
            index (int): Row index

        Returns:
            bool: Whether or not the index is checked
        """
        item = self.model().item(index, self.modelColumn())
        return item.checkState() == QtCore.Qt.Checked

    def setDefaultText(self, text):
        """
        Sets the text to display when no items are selected

        Args:
            text (str): Text to display
        """
        self._default_string = text
        self._set_selection_string()
        self.update()

    def setItemChecked(self, index, checked=True):
        """
        Args:
            index (int): Row index to modify
            checked (bool): Whether to check or uncheck the item
        """
        item = self._set_check_state(index, checked)
        self.itemStateChanged.emit(item)
        self._set_selection_string()

    # ======================================================================== #
    #  Protected
    # ======================================================================== #

    def _set_check_state(self, index, checked):
        # type: (int, bool) -> QtGui.QStandardItem
        item = self.model().item(index, self.modelColumn())
        item.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
        return item

    def _set_selection_string(self):
        selected = [i.data(QtCore.Qt.DisplayRole) for i in self.checkedItems()]
        if selected:
            self._selection_string = '({}) {}'.format(
                len(selected), ', '.join(selected))
        else:
            self._selection_string = self._default_string

    # ======================================================================== #
    #  Slots
    # ======================================================================== #

    def onItemPressed(self, index):
        # type: (QtCore.Qt.QModelIndex) -> None
        item = self.model().itemFromIndex(index)
        checked = item.checkState() == QtCore.Qt.Unchecked
        self.setItemChecked(index.row(), checked=checked)
        self._changed = True

    # ======================================================================== #
    #  Subclassed
    # ======================================================================== #

    def addItem(self, *args, **kwargs):
        super(ComboChecker, self).addItem(*args, **kwargs)
        self._set_check_state(self.count() - 1, False)

    def addItems(self, *args, **kwargs):
        count = self.count()
        super(ComboChecker, self).addItems(*args, **kwargs)
        for i in range(count, self.count()):
            self._set_check_state(i, False)

    def insertItem(self, index, *args, **kwargs):
        super(ComboChecker, self).insertItem(index, *args, **kwargs)
        self._set_check_state(index, False)

    def insertItems(self, index, *args, **kwargs):
        count = self.count()
        super(ComboChecker, self).insertItems(index, *args, **kwargs)
        added = self.count() - count
        for i in range(index, index + added):
            self._set_check_state(i, False)

    def hidePopup(self):
        if not self._changed:
            super(ComboChecker, self).hidePopup()
        self._changed = False

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = self._selection_string
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)
        painter.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, opt)
