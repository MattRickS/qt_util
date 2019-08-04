from PySide2 import QtCore, QtGui, QtWidgets


class HeaderRole(object):
    EditRole = QtCore.Qt.EditRole
    BackgroundColorRole = QtCore.Qt.UserRole + 101


class EditableHeaderView(QtWidgets.QHeaderView):
    MARGIN = 1

    stringEdited = QtCore.Signal(int, str)
    stringsReset = QtCore.Signal()

    def __init__(self, orientation):
        super(EditableHeaderView, self).__init__(orientation)
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
        text = self.get_string(logical_index)
        widget = QtWidgets.QLineEdit(self)
        widget.setText(text)
        widget.editingFinished.connect(self.finish_editing)
        return widget

    def edit_section(self, logical_index, focus_reason=QtCore.Qt.MouseFocusReason):
        """
        Args:
            logical_index (int): Section to begin editing
            focus_reason (QtCore.Qt.FocusReason): Reason to use when setting the
                widget's focus
        """
        if self._editing_widget:
            self.finish_editing()

        # Both internal states must be set together to avoid corrupted state during focus changes
        self._editing_index = logical_index
        self._editing_widget = self.create_widget(logical_index)

        rect = self.get_widget_geometry(logical_index)
        self._editing_widget.setGeometry(rect)
        self._editing_widget.show()
        self._editing_widget.setFocus(focus_reason)

    def finish_editing(self, accept_changes=True):
        """ Submits and kills the current widget being edited """
        if self._editing_widget is None:
            return

        try:
            if accept_changes:
                text = self.get_widget_text(self._editing_widget)
                self.set_string(self._editing_index, text)
        finally:
            # Internal state must be reset BEFORE abandoning the widget to GC.
            # Without this, there is a risk of focus state changes causing the
            # internal state to get corrupted and no widgets are closed.
            widget = self._editing_widget
            self.updateSection(self._editing_index)
            self._editing_widget = None
            self._editing_index = -1
            widget.setParent(None)

    def get_string(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the string value for

        Returns:
            str: Text stored for the section
        """
        return self.model().headerData(
            logical_index, self.orientation(), role=HeaderRole.EditRole
        )

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

    def set_string(self, logical_index, string):
        """
        Args:
            logical_index (int): Section to set the value for
            string (str): Text to set in the header
        """
        current = self.get_string(self._editing_index)
        if current == string:
            return

        edited = self.model().setHeaderData(
            logical_index, self.orientation(), string, HeaderRole.EditRole
        )
        self.updateSection(logical_index)
        if edited:
            self.stringEdited.emit(logical_index, string)

    # ======================================================================== #
    #  Subclassed
    # ======================================================================== #

    def focusNextPrevChild(self, is_next):
        # TODO: Focus is still behaving oddly for the view - it appears actual
        # ModelIndexes are being tabbed through as well, which can negatively
        # affect the viewport position
        if self._editing_index >= 0:
            if is_next:
                self.edit_section(
                    (self._editing_index + 1) % self.count(),
                    focus_reason=QtCore.Qt.TabFocusReason,
                )
            else:
                self.edit_section(
                    (self._editing_index - 1) % self.count(),
                    focus_reason=QtCore.Qt.BacktabFocusReason,
                )
            return True
        return super(EditableHeaderView, self).focusNextPrevChild(is_next)

    def mouseReleaseEvent(self, event):
        clickable = self.sectionsClickable()
        # Check if the release happens in the region of a widget and if so,
        # display the widget
        logical_index = self.logicalIndexAt(event.pos())
        rect = self.get_widget_geometry(logical_index)
        if rect.contains(event.pos()):
            self.edit_section(logical_index)
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
        option.text = self.get_string(logical_index)
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

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(EditableHeaderView, self).size()
        if self.orientation() == QtCore.Qt.Horizontal:
            return QtCore.QSize(size.width(), 46)
        else:
            # For some reason, vertical headers sizeHint doesn't work - must
            # provide a reasonable default. Even the height is ignored though.
            return QtCore.QSize(100, 46)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    class ExampleModel(QtCore.QAbstractItemModel):
        columns = ("one", "two", "three")

        def __init__(self, parent=None):
            # type: (QtWidgets.QWidget) -> None
            super(ExampleModel, self).__init__(parent)
            self._data = ["1", "2", "3"]
            self._h_strings = ["", "", ""]
            self._v_strings = ["", "", ""]

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
            elif role == HeaderRole.BackgroundColorRole:
                return QtGui.QColor("red")
            elif role == HeaderRole.EditRole:
                if orientation == QtCore.Qt.Horizontal:
                    return self._h_strings[section]
                else:
                    return self._v_strings[section]

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column)

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return 3

        def setHeaderData(self, section, orientation, value, role=QtCore.Qt.EditRole):
            if role == HeaderRole.EditRole:
                if orientation == QtCore.Qt.Horizontal:
                    self._h_strings[section] = str(value)
                else:
                    self._v_strings[section] = str(value)
                self.headerDataChanged.emit(orientation, section, section)
                return True
            return False

    def debug(*args, **kwargs):
        print("Signal received:", args, kwargs)

    model = ExampleModel()
    view = QtWidgets.QTableView()
    view.setModel(model)

    h_header = EditableHeaderView(QtCore.Qt.Horizontal)
    h_header.stringEdited.connect(debug)
    h_header.stringsReset.connect(debug)
    view.setHorizontalHeader(h_header)

    v_header = EditableHeaderView(QtCore.Qt.Vertical)
    v_header.stringEdited.connect(debug)
    v_header.stringsReset.connect(debug)
    view.setVerticalHeader(v_header)

    view.show()

    app.exec_()
    sys.exit()
