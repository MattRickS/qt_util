from PySide2 import QtCore, QtGui, QtWidgets


class EditableHeaderView(QtWidgets.QHeaderView):
    MARGIN = 1

    stringEdited = QtCore.Signal(int, str)
    stringsReset = QtCore.Signal()

    def __init__(self, orientation):
        super(EditableHeaderView, self).__init__(orientation)
        self._strings = []
        self._editing_widget = None
        self._editing_index = -1
        self._dummy_edit = QtWidgets.QLineEdit()

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

    @property
    def edit_index(self):
        """
        Returns:
            int: Logical index currently being edited, or -1 if nothing is being
                edited
        """
        return self._editing_index

    def create_widget(self, logical_index):
        """
        Creates the widget for the index

        Args:
            logical_index (int): Section to create the widget for

        Returns:
            QtWidgets.QWidget: Created widget
        """
        # Can be subclassed for custom widgets
        text = self._strings[logical_index]
        widget = QtWidgets.QLineEdit(self)
        widget.setText(text)
        widget.editingFinished.connect(self.finalise_widget)
        return widget

    def edit_widget(self, logical_index, focus_reason=QtCore.Qt.MouseFocusReason):
        """
        Args:
            logical_index (int): Section to begin editing
            focus_reason (QtCore.Qt.FocusReason): Reason to use when setting the
                widget's focus
        """
        if self._editing_widget:
            self.finalise_widget()

        rect = self.get_widget_geometry(logical_index)
        self._editing_widget = self.create_widget(logical_index)
        self._editing_widget.setFocus(focus_reason)
        self._editing_widget.setGeometry(rect)
        self._editing_widget.show()
        self._editing_index = logical_index

    def finalise_widget(self):
        """ Submits and kills the current widget being edited """
        if self._editing_widget is None:
            return

        self._editing_widget.blockSignals(True)
        try:
            text = self.get_widget_text(self._editing_widget)
            self.set_string(self._editing_index, text)
        finally:
            self._editing_widget.setParent(None)
            self._editing_widget.deleteLater()
            self._editing_widget = None
            self._editing_index = -1

    def get_string(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the string value for

        Returns:
            str: Text stored for the section
        """
        return self._strings[logical_index]

    def get_strings(self):
        """
        Returns:
            list[str]: List of strings ordered by logical index
        """
        return self._strings[:]

    def get_widget_text(self, widget):
        """
        Args:
            widget (QtWidgets.QWidget): Widget created by create_widget

        Returns:
            str: Text value represented in the widget
        """
        return widget.text()

    def get_header_geometry(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the header geometry for

        Returns:
            QtCore.QRect: The geometry rect within the header without the widget
        """
        if self.orientation() == QtCore.Qt.Horizontal:
            half_height = self.height() * 0.5
            return QtCore.QRect(
                self.sectionViewportPosition(logical_index),
                0,
                self.sectionSize(logical_index),
                half_height,
            )
        else:
            # half_width = self.width() * 0.5
            # return QtCore.QRect(
            #     0,
            #     self.sectionViewportPosition(logical_index) + self.MARGIN,
            #     half_width,
            #     self.sectionSize(logical_index) - self.MARGIN * 2,
            # )

            half_height = self.sectionSize(logical_index) * 0.5
            return QtCore.QRect(
                self.MARGIN,
                self.sectionViewportPosition(logical_index),
                self.width() - self.MARGIN * 2,
                half_height,
            )

    def get_widget_geometry(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the header geometry for

        Returns:
            QtCore.QRect: The geometry rect within the header for the widget
        """
        if self.orientation() == QtCore.Qt.Horizontal:
            half_height = self.height() * 0.5
            return QtCore.QRect(
                self.sectionViewportPosition(logical_index) + self.MARGIN,
                half_height,
                self.sectionSize(logical_index) - self.MARGIN * 2,
                half_height,
            )
        else:
            # half_width = self.width() * 0.5
            # return QtCore.QRect(
            #     half_width,
            #     self.sectionViewportPosition(logical_index) + self.MARGIN,
            #     half_width,
            #     self.sectionSize(logical_index) - self.MARGIN * 2,
            # )

            half_height = self.sectionSize(logical_index) * 0.5
            return QtCore.QRect(
                self.MARGIN,
                self.sectionViewportPosition(logical_index) + half_height,
                self.width() - self.MARGIN * 2,
                half_height,
            )

    def reset_strings(self):
        """ Clears all string values """
        self._strings = [""] * self.count()
        self.stringsReset.emit()

    def set_string(self, logical_index, string):
        """
        Args:
            logical_index (int): Section to set the value for
            string (str): Text to set in the header
        """
        if self._strings[logical_index] == string:
            return
        self._strings[logical_index] = string
        self.stringEdited.emit(logical_index, string)
        self.updateSection(logical_index)

    def set_strings(self, strings):
        """
        Raises:
            ValueError: If the number of strings don't match the section count

        Args:
            strings (list[str]): List of strings to set - must be the same
                number of sections in the model
        """
        if len(strings) != self.count():
            raise ValueError(
                "Invalid number of strings: {}/{}".format(len(strings), self.count())
            )
        self._strings = list(strings)
        self.update()
        self.stringsReset.emit()

    def on_sections_inserted(self, index, first, last):
        self._strings[first:first] = [""] * (1 + last - first)

    def on_sections_removed(self, index, first, last):
        del self._strings[first : last + 1]

    # ======================================================================== #
    #  Events
    # ======================================================================== #

    def mouseReleaseEvent(self, event):
        clickable = self.sectionsClickable()
        # Check if the release happens in the region of a widget and if so,
        # display the widget
        logical_index = self.logicalIndexAt(event.pos())
        rect = self.get_widget_geometry(logical_index)
        if rect.contains(event.pos()):
            self.edit_widget(logical_index)
            # Prevent interaction with the widget region from triggering a
            # section click, otherwise it will be sorted (if sorting is
            # enabled). Note: setSortIndicator is not virtual so overriding
            # it explicitly is not possible
            self.setSectionsClickable(False)
        super(EditableHeaderView, self).mouseReleaseEvent(event)
        if self.sectionsClickable() != clickable:
            self.setSectionsClickable(clickable)

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        # Render the filter widget in the header widget rect
        painter.save()

        widget_rect = self.get_widget_geometry(logical_index)

        option = QtWidgets.QStyleOptionFrame()
        option.initFrom(self._dummy_edit)
        option.rect = widget_rect
        option.lineWidth = self.style().pixelMetric(
            QtWidgets.QStyle.PM_DefaultFrameWidth, option, self._dummy_edit
        )
        option.midLineWidth = 0
        option.state |= QtWidgets.QStyle.State_Sunken
        option.text = self._strings[logical_index]
        option.features = 0
        # option.palette.setBrush(QtGui.QPalette.Base, QtGui.QColor("white"))

        style = self.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelLineEdit, option, painter, self)
        contents_rect = style.subElementRect(
            QtWidgets.QStyle.SE_LineEditContents, option, self._dummy_edit
        )
        style.drawItemText(
            painter,
            contents_rect,
            QtCore.Qt.AlignCenter,
            option.palette,
            True,
            option.text,
        )

        painter.restore()

        # # Render the original header section in the remaining area
        header_geo = self.get_header_geometry(logical_index)
        super(EditableHeaderView, self).paintSection(painter, header_geo, logical_index)

    def setModel(self, model):
        super(EditableHeaderView, self).setModel(model)
        if self.orientation() == QtCore.Qt.Horizontal:
            model.columnsInserted.connect(self.on_sections_inserted)
            model.columnsRemoved.connect(self.on_sections_removed)
        else:
            model.rowsInserted.connect(self.on_sections_inserted)
            model.rowsRemoved.connect(self.on_sections_removed)
        self.reset_strings()

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(EditableHeaderView, self).size()
        print(size)
        if self.orientation() == QtCore.Qt.Horizontal:
            return QtCore.QSize(size.width(), 46)
        else:
            # For some reason, vertical headers sizeHint doesn't work - must
            # provide a reasonable default. Even the height is ignored though.
            return QtCore.QSize(100, 46)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    class EntityModel(QtCore.QAbstractItemModel):
        columns = ("one", "two", "three")

        def __init__(self, entities=None, parent=None):
            # type: (list, QtWidgets.QWidget) -> None
            super(EntityModel, self).__init__(parent)
            self._data = ["1", "2", "3"]

        def columnCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return 3

        def data(self, index, role=QtCore.Qt.DisplayRole):
            # type: (QtCore.QModelIndex, int) -> object
            if not index.isValid():
                return
            if role == QtCore.Qt.DisplayRole:
                return self._data[index.column()]

        def flags(self, index):
            # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
            # type: (int, QtCore.Qt.Orientation, int) -> str
            if role == QtCore.Qt.DisplayRole:
                return self.columns[section]

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column)

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return 3

    model = EntityModel()
    view = QtWidgets.QTableView()
    view.setModel(model)
    h_header = EditableHeaderView(QtCore.Qt.Horizontal)
    view.setHorizontalHeader(h_header)
    v_header = EditableHeaderView(QtCore.Qt.Vertical)
    view.setVerticalHeader(v_header)
    view.show()

    app.exec_()
    sys.exit()
