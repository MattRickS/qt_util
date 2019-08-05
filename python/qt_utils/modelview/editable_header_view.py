from PySide2 import QtCore, QtGui, QtWidgets


class HeaderRole(object):
    EditRole = QtCore.Qt.EditRole
    BackgroundColorRole = QtCore.Qt.UserRole + 101
    EditableRole = QtCore.Qt.UserRole + 102
    ChoicesRole = QtCore.Qt.UserRole + 103


class HeaderIndex(object):
    def __init__(self, model, orientation, section):
        self.model = model
        self.orientation = orientation
        self.section = section

    def data(self, role=HeaderRole.EditRole):
        return self.model.headerData(self.section, self.orientation, role)

    def setData(self, value, role=HeaderRole.EditRole):
        return self.model.setHeaderData(self.section, self.orientation, value, role)


class HeaderDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HeaderDelegate, self).__init__(parent)
        self._dummy = QtWidgets.QLineEdit()

    def createEditor(self, parent, option, header_index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionFrame, HeaderIndex) -> QtWidgets.QWidget
        editor = QtWidgets.QLineEdit(parent)
        editor.editingFinished.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, header_index):
        # type: (QtWidgets.QWidget, HeaderIndex) -> None
        string = header_index.data()
        editor.setText(string)

    def setModelData(self, editor, model, header_index):
        # type: (QtWidgets.QWidget, QtCore.QAbstractItemModel, HeaderIndex) -> None
        string = editor.text()
        model.setHeaderData(
            header_index.section, header_index.orientation, string, HeaderRole.EditRole
        )

    def paint(self, painter, option, header_index):
        # type: (QtGui.QPainterPath, QtGui.QStyleOptionFrame, HeaderIndex) -> None
        painter.save()

        style = QtWidgets.QApplication.style()
        frame_option = QtWidgets.QStyleOptionFrame()
        frame_option.initFrom(self._dummy)
        frame_option.rect = option.rect
        frame_option.lineWidth = style.pixelMetric(
            QtWidgets.QStyle.PM_DefaultFrameWidth, frame_option, self._dummy
        )
        frame_option.midLineWidth = 0
        frame_option.state |= QtWidgets.QStyle.State_Sunken
        if not header_index.data(HeaderRole.EditableRole):
            frame_option ^= QtWidgets.QStyle.State_Enabled
        frame_option.text = header_index.data()
        frame_option.features = 0
        # option.palette.setBrush(QtGui.QPalette.Base, QtGui.QColor("white"))

        style.drawPrimitive(
            QtWidgets.QStyle.PE_PanelLineEdit, frame_option, painter, self.parent()
        )
        contents_rect = style.subElementRect(
            QtWidgets.QStyle.SE_LineEditContents, frame_option, self._dummy
        )
        style.drawItemText(
            painter,
            contents_rect,
            QtCore.Qt.AlignCenter,
            frame_option.palette,
            True,
            frame_option.text,
        )

        painter.restore()

    def sizeHint(self, option, header_index):
        # type: (QtGui.QStyleOptionFrame, HeaderIndex) -> QtCore.QSize
        return QtCore.QSize(100, 46)

    def updateEditorGeometry(self, editor, option, header_index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionFrame, HeaderIndex) -> None
        editor.setGeometry(option.rect)


class ComboHeaderDelegate(HeaderDelegate):
    def __init__(self, parent=None, choices_role=HeaderRole.ChoicesRole):
        super(ComboHeaderDelegate, self).__init__(parent)
        self._dummy = QtWidgets.QComboBox()
        self._choices_role = choices_role

    def createEditor(self, parent, option, header_index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionFrame, HeaderIndex) -> QtWidgets.QComboBox
        choices = header_index.data(self._choices_role)
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(choices)
        editor.activated.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, header_index):
        # type: (QtWidgets.QComboBox, HeaderIndex) -> None
        current = header_index.data()
        editor.setCurrentText(current)
        editor.showPopup()

    def setModelData(self, editor, model, header_index):
        # type: (QtWidgets.QComboBox, QtCore.QAbstractItemModel, HeaderIndex) -> None
        value = editor.currentText()
        model.setHeaderData(
            header_index.section, header_index.orientation, value, HeaderRole.EditRole
        )

    def paint(self, painter, option, header_index):
        # type: (QtGui.QPainterPath, QtGui.QStyleOptionFrame, HeaderIndex) -> None
        painter.save()

        style = QtWidgets.QApplication.style()
        opt = QtWidgets.QStyleOptionComboBox()
        opt.initFrom(self._dummy)
        opt.rect = option.rect
        opt.currentText = header_index.data()
        style.drawComplexControl(
            QtWidgets.QStyle.CC_ComboBox, opt, painter, self._dummy
        )
        style.drawControl(QtWidgets.QStyle.CE_ComboBoxLabel, opt, painter, self._dummy)

        painter.restore()


class EditableHeaderView(QtWidgets.QHeaderView):
    MARGIN = 1

    Right = 0
    Below = 1

    def __init__(self, orientation, positioning=Below):
        super(EditableHeaderView, self).__init__(orientation)
        if positioning not in (self.Right, self.Below):
            raise ValueError("Unknown positioning: {}".format(self._positioning))

        self._positioning = positioning

        self._editing_widget = None
        self._editing_index = -1
        self.setItemDelegate(HeaderDelegate(self))

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        if orientation == QtCore.Qt.Vertical and self._positioning == self.Below:
            self.setDefaultSectionSize(46)

    @property
    def edit_index(self):
        """
        Returns:
            int: Logical index currently being edited, or -1 if nothing is being
                edited
        """
        return self._editing_index

    def edit_section(self, logical_index, focus_reason=QtCore.Qt.MouseFocusReason):
        """
        Args:
            logical_index (int): Section to begin editing
            focus_reason (QtCore.Qt.FocusReason): Reason to use when setting the
                widget's focus
        """
        if self._editing_widget:
            self.finish_editing()

        header_index = self.header_index(logical_index)
        delegate = self.item_delegate_for_section(logical_index)

        # Both internal states must be set together to avoid corrupted state during focus changes
        self._editing_index = logical_index
        self._editing_widget = delegate.createEditor(
            self, QtWidgets.QStyleOptionFrame(), header_index
        )
        # TODO: At the moment nothing knows when to close the delegate unless
        # the delegate itself specifies it. Ideally there should be an event
        # filter of some sort for deducing when an editor can be closed

        rect = self.get_widget_geometry(logical_index)
        self._editing_widget.setGeometry(rect)

        delegate.setEditorData(self._editing_widget, header_index)
        self._editing_widget.show()
        self._editing_widget.setFocus(focus_reason)

    def finish_editing(self, accept_changes=True):
        """ Submits and kills the current widget being edited """
        if self._editing_widget is None:
            return

        try:
            if accept_changes:
                delegate = self.item_delegate_for_section(self._editing_index)
                header_index = self.header_index(self._editing_index)
                delegate.setModelData(self._editing_widget, self.model(), header_index)
        finally:
            # Internal state must be reset BEFORE abandoning the widget to GC.
            # Without this, there is a risk of focus state changes causing the
            # internal state to get corrupted and no widgets are closed.
            widget = self._editing_widget
            self.updateSection(self._editing_index)
            self._editing_widget = None
            self._editing_index = -1
            widget.setParent(None)

    def get_header_geometry(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the header geometry for

        Returns:
            QtCore.QRect: The geometry rect within the header without the widget
        """
        if self.orientation() == QtCore.Qt.Horizontal:
            if self._positioning == self.Below:
                half_height = self.height() * 0.5
                return QtCore.QRect(
                    self.sectionViewportPosition(logical_index),
                    0,
                    self.sectionSize(logical_index),
                    half_height,
                )
            elif self._positioning == self.Right:
                half_width = self.sectionSize(logical_index) * 0.5
                return QtCore.QRect(
                    self.sectionViewportPosition(logical_index),
                    0,
                    half_width,
                    self.height(),
                )
            else:
                raise ValueError("Unknown positioning: {}".format(self._positioning))
        else:
            if self._positioning == self.Below:
                half_height = self.sectionSize(logical_index) * 0.5
                return QtCore.QRect(
                    self.MARGIN,
                    self.sectionViewportPosition(logical_index),
                    self.width() - self.MARGIN * 2,
                    half_height,
                )
            elif self._positioning == self.Right:
                half_width = self.width() * 0.5
                return QtCore.QRect(
                    0,
                    self.sectionViewportPosition(logical_index) + self.MARGIN,
                    half_width,
                    self.sectionSize(logical_index) - self.MARGIN * 2,
                )
            else:
                raise ValueError("Unknown positioning: {}".format(self._positioning))

    def get_widget_geometry(self, logical_index):
        """
        Args:
            logical_index (int): Section to get the header geometry for

        Returns:
            QtCore.QRect: The geometry rect within the header for the widget
        """
        if self.orientation() == QtCore.Qt.Horizontal:
            if self._positioning == self.Below:
                half_height = self.height() * 0.5
                return QtCore.QRect(
                    self.sectionViewportPosition(logical_index) + self.MARGIN,
                    half_height,
                    self.sectionSize(logical_index) - self.MARGIN * 2,
                    half_height,
                )
            elif self._positioning == self.Right:
                half_width = self.sectionSize(logical_index) * 0.5
                return QtCore.QRect(
                    self.sectionViewportPosition(logical_index) + half_width,
                    0,
                    half_width,
                    self.height(),
                )
            else:
                raise ValueError("Unknown positioning: {}".format(self._positioning))
        else:
            if self._positioning == self.Below:
                half_height = self.sectionSize(logical_index) * 0.5
                return QtCore.QRect(
                    self.MARGIN,
                    self.sectionViewportPosition(logical_index) + half_height,
                    self.width() - self.MARGIN * 2,
                    half_height,
                )
            elif self._positioning == self.Right:
                half_width = self.width() * 0.5
                return QtCore.QRect(
                    half_width,
                    self.sectionViewportPosition(logical_index) + self.MARGIN,
                    half_width,
                    self.sectionSize(logical_index) - self.MARGIN * 2,
                )
            else:
                raise ValueError("Unknown positioning: {}".format(self._positioning))

    def header_index(self, logical_index):
        # type: (int) -> HeaderIndex
        return HeaderIndex(self.model(), self.orientation(), logical_index)

    def item_delegate_for_section(self, section):
        # type: (int) -> HeaderDelegate
        delegate = (
            self.itemDelegateForColumn(section)
            if self.orientation() == QtCore.Qt.Horizontal
            else self.itemDelegateForRow(section)
        )
        return delegate or self.itemDelegate()

    def set_item_delegate_for_section(self, section, delegate):
        # type: (int, HeaderDelegate) -> None
        if self.orientation() == QtCore.Qt.Horizontal:
            self.setItemDelegateForColumn(section, delegate)
        else:
            self.setItemDelegateForRow(section, delegate)

    def on_close_editor(self):
        self.finish_editing(accept_changes=False)

    def on_commit_data(self):
        self.finish_editing()

    def _connect_delegate(self, delegate):
        if delegate is None:
            return
        delegate.commitData.connect(self.on_commit_data)
        delegate.closeEditor.connect(self.on_close_editor)

    def _disconnect_delegate(self, delegate):
        if delegate is None:
            return
        delegate.commitData.disconnect(self.on_commit_data)
        delegate.closeEditor.disconnect(self.on_close_editor)

    # ======================================================================== #
    #  Subclassed
    # ======================================================================== #

    def currentChanged(self, current, old):
        super(EditableHeaderView, self).currentChanged(current, old)
        # If a cell is selected, the widget is no longer in focus
        self.finish_editing()

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

    def headerDataChanged(self, orientation, first, last):
        # type: (QtCore.Qt.Orientation, int, int) -> None
        for i in range(first, last + 1):
            self.updateSection(i)

    def mousePressEvent(self, event):
        clickable = self.sectionsClickable()
        # Check if the release happens in the region of a widget and if so,
        # display the widget
        logical_index = self.logicalIndexAt(event.pos())
        rect = self.get_widget_geometry(logical_index)
        if rect.contains(event.pos()):
            # Prevent interaction with the widget region from triggering a
            # section click, otherwise it will be sorted (if sorting is
            # enabled). Note: setSortIndicator is not virtual so overriding
            # it explicitly is not possible
            self.setSectionsClickable(False)
        super(EditableHeaderView, self).mouseReleaseEvent(event)
        if self.sectionsClickable() != clickable:
            self.setSectionsClickable(clickable)

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

        option = QtWidgets.QStyleOptionFrame()
        option.rect = self.get_widget_geometry(logical_index)
        option.state |= QtWidgets.QStyle.State_Sunken
        # option.palette.setBrush(QtGui.QPalette.Base, QtGui.QColor("white"))

        painter.save()
        delegate = self.item_delegate_for_section(logical_index)
        delegate.paint(painter, option, self.header_index(logical_index))
        painter.restore()

        # # Render the original header section in the remaining area
        header_geo = self.get_header_geometry(logical_index)
        super(EditableHeaderView, self).paintSection(painter, header_geo, logical_index)

    def setItemDelegate(self, delegate):
        # type: (HeaderDelegate) -> None
        old_delegate = self.itemDelegate()
        self._disconnect_delegate(old_delegate)
        super(EditableHeaderView, self).setItemDelegate(delegate)
        new_delegate = self.itemDelegate()
        self._connect_delegate(new_delegate)

    def setItemDelegateForColumn(self, column, delegate):
        # type: (int, HeaderDelegate) -> None
        super(EditableHeaderView, self).setItemDelegateForColumn(column, delegate)
        new_delegate = self.itemDelegateForColumn(column)
        self._connect_delegate(new_delegate)

    def setItemDelegateForRow(self, row, delegate):
        # type: (int, HeaderDelegate) -> None
        super(EditableHeaderView, self).setItemDelegateForRow(row, delegate)
        new_delegate = self.itemDelegateForRow(row)
        self._connect_delegate(new_delegate)

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(EditableHeaderView, self).sizeHint()
        if self._positioning == self.Right:
            width = size.width() + 100
            height = size.height()
        elif self._positioning == self.Below:
            width = size.width()
            height = size.height() * 2
        else:
            raise ValueError("Unknown positioning: {}".format(self._positioning))

        size = QtCore.QSize(width, height)
        return size

    def viewportEvent(self, event):
        # Update the geometry of any widget being edited if the viewport is resized
        if isinstance(event, QtGui.QResizeEvent) and self._editing_widget is not None:
            widget_rect = self.get_widget_geometry(self._editing_index)
            self._editing_widget.setGeometry(widget_rect)
        return super(EditableHeaderView, self).viewportEvent(event)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    class ExampleModel(QtCore.QAbstractItemModel):
        columns = ("one", "two", "three")

        def __init__(self, parent=None):
            # type: (QtWidgets.QWidget) -> None
            super(ExampleModel, self).__init__(parent)
            self._data = ["1", "2", "3"]
            self._h_strings = ["", "ghi", ""]
            self._v_strings = ["", "", "789"]

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
            # type: (int, QtCore.Qt.Orientation, int) -> object
            if role == QtCore.Qt.DisplayRole:
                return self.columns[section]
            elif role == HeaderRole.BackgroundColorRole:
                return QtGui.QColor("red")
            elif role == HeaderRole.EditableRole:
                return True
            elif role == HeaderRole.EditRole:
                if orientation == QtCore.Qt.Horizontal:
                    return self._h_strings[section]
                else:
                    return self._v_strings[section]
            elif role == HeaderRole.ChoicesRole:
                return ["abc", "def", "ghi"]

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
                value = str(value)
                string_list = (
                    self._h_strings
                    if orientation == QtCore.Qt.Horizontal
                    else self._v_strings
                )
                if string_list[section] != value:
                    string_list[section] = value
                    self.headerDataChanged.emit(orientation, section, section)
                    return True

            return False

    model = ExampleModel()
    view = QtWidgets.QTableView()
    view.setModel(model)

    h_header = EditableHeaderView(QtCore.Qt.Horizontal)
    view.setHorizontalHeader(h_header)

    v_header = EditableHeaderView(QtCore.Qt.Vertical)
    view.setVerticalHeader(v_header)

    combo_delegate = ComboHeaderDelegate(view)
    h_header.set_item_delegate_for_section(1, combo_delegate)

    view.show()

    def debug(*args, **kwargs):
        print(args, kwargs)

    model.headerDataChanged.connect(debug)

    app.exec_()
    sys.exit()
