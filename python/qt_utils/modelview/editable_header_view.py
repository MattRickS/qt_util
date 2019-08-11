import contextlib

from PySide2 import QtCore, QtGui, QtWidgets


class HeaderRole(object):
    EditRole = QtCore.Qt.EditRole
    BackgroundColorRole = QtCore.Qt.UserRole + 101
    EditableRole = QtCore.Qt.UserRole + 102
    ChoicesRole = QtCore.Qt.UserRole + 103
    FilterTypeRole = QtCore.Qt.UserRole + 104
    CaseSensitivityRole = QtCore.Qt.UserRole + 105


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
        editor.setGeometry(option.rect)
        # TODO: Method for whether or not filters should be applied on
        # textChanged instead of editingFinished
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
        opt = QtWidgets.QStyleOptionFrame()
        opt.initFrom(self._dummy)
        opt.rect = option.rect
        opt.lineWidth = style.pixelMetric(
            QtWidgets.QStyle.PM_DefaultFrameWidth, opt, self._dummy
        )
        opt.midLineWidth = 0
        opt.state |= QtWidgets.QStyle.State_Sunken
        is_enabled = (
            bool(option.state & QtWidgets.QStyle.State_Enabled)
            and header_index.data(HeaderRole.EditableRole) is not False
        )
        if is_enabled:
            opt.state |= QtWidgets.QStyle.State_Enabled
            opt.state &= ~QtWidgets.QStyle.State_ReadOnly
        else:
            opt.state |= QtWidgets.QStyle.State_ReadOnly
            opt.state &= ~QtWidgets.QStyle.State_Enabled
        opt.text = header_index.data()
        opt.features = 0

        bg_colour = model.headerData(
            header_index.section,
            header_index.orientation,
            HeaderRole.BackgroundColorRole,
        )
        if bg_colour is not None:
            opt.palette.setBrush(self._dummy.backgroundRole(), bg_colour)

        style.drawPrimitive(
            QtWidgets.QStyle.PE_PanelLineEdit, opt, painter, self.parent()
        )
        contents_rect = style.subElementRect(
            QtWidgets.QStyle.SE_LineEditContents, opt, self._dummy
        )
        style.drawItemText(
            painter,
            contents_rect,
            QtCore.Qt.AlignCenter,
            opt.palette,
            is_enabled,
            opt.text,
            QtGui.QPalette.Text if is_enabled else QtGui.QPalette.Shadow,
        )

        painter.restore()

    def sizeHint(self, option, header_index):
        # type: (QtGui.QStyleOptionFrame, HeaderIndex) -> QtCore.QSize
        return QtCore.QSize(100, 46)

    def updateEditorGeometry(self, editor, option, header_index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionFrame, HeaderIndex) -> None
        editor.setGeometry(option.rect)


class Menu(QtWidgets.QListWidget):
    focusLost = QtCore.Signal()
    focusTabbed = QtCore.Signal(bool)

    def __init__(self, parent, max_row_height):
        super(Menu, self).__init__(parent)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self._max_row_height = max_row_height

    def focusOutEvent(self, event):
        super(Menu, self).focusOutEvent(event)
        self.focusLost.emit()

    def focusNextPrevChild(self, is_next):
        self.focusTabbed.emit(is_next)
        return False


class ComboHeaderDelegate(HeaderDelegate):
    def __init__(self, parent, choices_role=HeaderRole.ChoicesRole, max_row_height=8):
        super(ComboHeaderDelegate, self).__init__(parent)
        self._choices_role = choices_role
        self._max_row_height = max_row_height

    def _move_focus(self, header_index, is_next):
        parent = self.parent()
        if parent is None or not isinstance(parent, QtWidgets.QAbstractItemView):
            return

        if header_index.orientation == QtCore.Qt.Horizontal:
            header = parent.horizontalHeader()
        else:
            header = parent.verticalHeader()
        header.focusNextPrevChild(is_next)

    def createEditor(self, parent, option, header_index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionFrame, HeaderIndex) -> QtWidgets.QComboBox
        choices = header_index.data(self._choices_role) or []
        editor = Menu(parent, self._max_row_height)
        editor.setFixedWidth(option.rect.width())
        editor.addItems(choices)

        # Position it over the header widget
        pos = option.rect.topLeft()
        global_pos = parent.mapToGlobal(pos)
        editor.move(global_pos)

        # Ensure the dropdown only displays the available items
        rect = self.parent().rect()
        remaining_height = rect.height() - pos.y()
        margins = editor.contentsMargins()
        editor.setMaximumHeight(
            min(
                remaining_height,
                (min(self._max_row_height, editor.count())) * editor.sizeHintForRow(0)
                + margins.top()
                + margins.bottom()
            )
        )
        editor.show()

        editor.focusTabbed.connect(lambda x: self._move_focus(header_index, x))
        editor.focusLost.connect(lambda: self.closeEditor.emit(editor))
        editor.itemClicked.connect(lambda: self.commitData.emit(editor))

        return editor

    def setEditorData(self, editor, header_index):
        # type: (Menu, HeaderIndex) -> None
        value = header_index.data()
        if value is None:
            return

        items = editor.findItems(value, QtCore.Qt.MatchExactly)
        if len(items) != 1:
            return
        editor.setItemSelected(items[0], True)

    def setModelData(self, editor, model, header_index):
        # type: (QtWidgets.QComboBox, QtCore.QAbstractItemModel, HeaderIndex) -> None
        selected_items = editor.selectedItems()
        if len(selected_items) != 1:
            return
        value = selected_items[0].text()
        model.setHeaderData(
            header_index.section, header_index.orientation, value, HeaderRole.EditRole
        )

    def paint(self, painter, option, header_index):
        # type: (QtGui.QPainter, QtGui.QStyleOptionFrame, HeaderIndex) -> None
        super(ComboHeaderDelegate, self).paint(painter, option, header_index)

        painter.save()

        is_enabled = (
            bool(option.state & QtWidgets.QStyle.State_Enabled)
            and header_index.data(HeaderRole.EditableRole) is not False
        )
        role = QtGui.QPalette.Active if is_enabled else QtGui.QPalette.Inactive
        arrow_brush = option.palette.brush(role, QtGui.QPalette.Text)
        painter.setBrush(arrow_brush)

        style = QtWidgets.QApplication.style()
        opt = QtWidgets.QStyleOptionComboBox()
        opt.rect = option.rect
        ar = style.proxy().subControlRect(
            QtWidgets.QStyle.CC_ComboBox, opt, QtWidgets.QStyle.SC_ComboBoxArrow
        )
        center = ar.center()
        painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        painter.drawPolygon(
            [
                center - QtCore.QPoint(4, 2),
                center + QtCore.QPoint(4, -2),
                center + QtCore.QPoint(0, 2),
            ]
        )

        painter.restore()


class EditableHeaderView(QtWidgets.QHeaderView):
    MARGIN = 1

    Right = 0
    Below = 1
    Fill = 2

    def __init__(self, orientation, positioning=Below):
        super(EditableHeaderView, self).__init__(orientation)
        if positioning not in (self.Right, self.Below, self.Fill):
            raise ValueError("Unknown positioning: {}".format(positioning))

        self._positioning = positioning

        self._editing_widget = None
        self._editing_index = -1
        self.setItemDelegate(HeaderDelegate(self))

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        # The only way to reliably ensure the row height will fit both the
        # header and widget by default.
        if orientation == QtCore.Qt.Vertical and self._positioning == self.Below:
            self.setDefaultSectionSize(46)

    @property
    def editing_index(self):
        """
        Returns:
            int: Logical index currently being edited, or -1 if nothing is being
                edited
        """
        return self._editing_index

    def clear_section(self, logical_index):
        if (
            self.model().headerData(
                logical_index, self.orientation(), HeaderRole.EditableRole
            )
            is False
        ):
            print("Section is not editable: {}".format(logical_index))
            return
        self.model().setHeaderData(
            logical_index, self.orientation(), "", HeaderRole.EditRole
        )

    def edit_section(self, logical_index, focus_reason=QtCore.Qt.MouseFocusReason):
        """
        Args:
            logical_index (int): Section to begin editing
            focus_reason (QtCore.Qt.FocusReason): Reason to use when setting the
                widget's focus
        """
        if self._editing_widget:
            self.finish_editing()

        # If EditableRole is not defined, assume True. If explicitly set to False, prevent editing
        if (
            self.model().headerData(
                logical_index, self.orientation(), HeaderRole.EditableRole
            )
            is False
        ):
            print("Section is not editable: {}".format(logical_index))
            return

        header_index = self.header_index(logical_index)
        delegate = self.item_delegate_for_section(logical_index)
        widget_rect = self.get_widget_geometry(logical_index)

        opt = self.get_section_style_option(logical_index)
        opt.rect = widget_rect

        # Both internal states must be set together to avoid corrupted state during focus changes
        self._editing_index = logical_index
        self._editing_widget = delegate.createEditor(self, opt, header_index)
        # TODO: At the moment nothing knows when to close the delegate unless
        # the delegate itself specifies it. Ideally there should be an event
        # filter of some sort for deducing when an editor can be closed

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
            if widget is not None:
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
            elif self._positioning == self.Fill:
                return QtCore.QRect()
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
            elif self._positioning == self.Fill:
                return QtCore.QRect()
            else:
                raise ValueError("Unknown positioning: {}".format(self._positioning))

    def get_section_style_option(self, logical_index):
        # type: (int) -> QtWidgets.QStyleOptionHeader
        model = self.model()
        orientation = self.orientation()
        root = self.rootIndex()
        selection_model = self.selectionModel()
        style = self.style()

        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)

        # State
        state = QtWidgets.QStyle.State_None
        if self.isEnabled():
            state |= QtWidgets.QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QtWidgets.QStyle.State_Active
        if self.sectionsClickable() and selection_model and self.highlightSections():
            if orientation == QtCore.Qt.Horizontal:
                if selection_model.columnIntersectsSelection(logical_index, root):
                    state |= QtWidgets.QStyle.State_On
                if selection_model.isColumnSelected(logical_index, root):
                    state |= QtWidgets.QStyle.State_Sunken
            else:
                if selection_model.rowIntersectsSelection(logical_index, root):
                    state |= QtWidgets.QStyle.State_On
                if selection_model.isRowSelected(logical_index, root):
                    state |= QtWidgets.QStyle.State_Sunken
        opt.state |= state

        # Margin
        margin = 2 * style.pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, self)
        header_arrow_alignment = style.styleHint(
            QtWidgets.QStyle.SH_Header_ArrowAlignment, opt, self
        )
        is_header_arrow_on_the_side = header_arrow_alignment & QtCore.Qt.AlignVCenter
        if (
            self.isSortIndicatorShown()
            and self.sortIndicatorSection() == logical_index
            and is_header_arrow_on_the_side
        ):
            margin += style.pixelMetric(QtWidgets.QStyle.PM_HeaderMarkSize, opt, self)

        # Icon
        opt.iconAlignment = QtCore.Qt.AlignVCenter
        icon = model.headerData(logical_index, orientation, QtCore.Qt.DecorationRole)
        if icon and not icon.isNull():
            opt.icon = icon
            margin += style.pixelMetric(
                QtWidgets.QStyle.PM_SmallIconSize, opt, self
            ) + style.pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, self)

        # Text
        text_alignment = model.headerData(
            logical_index, orientation, QtCore.Qt.TextAlignmentRole
        )

        opt.textAlignment = text_alignment or self.defaultAlignment()
        opt.text = model.headerData(logical_index, orientation, QtCore.Qt.DisplayRole)
        if self.textElideMode() != QtCore.Qt.ElideNone:
            text_rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderLabel, opt, self)
            opt.text = opt.fontMetrics.elidedText(
                opt.text, self.textElideMode(), text_rect.width() - margin
            )

        # Brushes
        background_brush = model.headerData(
            logical_index, orientation, QtCore.Qt.BackgroundRole
        )
        if background_brush is not None:
            brush = QtGui.QBrush(background_brush)
            opt.palette.setBrush(QtGui.QPalette.Button, brush)
            opt.palette.setBrush(QtGui.QPalette.Window, brush)

        foreground_brush = model.headerData(
            logical_index, orientation, QtCore.Qt.ForegroundRole
        )
        if foreground_brush is not None:
            opt.palette.setBrush(
                QtGui.QPalette.ButtonText, QtGui.QBrush(foreground_brush)
            )

        # Header section attributes
        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logical_index:
            opt.sortIndicator = (
                QtWidgets.QStyleOptionHeader.SortDown
                if (self.sortIndicatorOrder() == QtCore.Qt.AscendingOrder)
                else QtWidgets.QStyleOptionHeader.SortUp
            )
        opt.section = logical_index
        opt.orientation = orientation

        # Position
        visual = self.visualIndex(logical_index)
        first = self.logicalIndex(0) == logical_index
        last = self.logicalIndex(self.count() - 1) == logical_index
        if first and last:
            opt.position = QtWidgets.QStyleOptionHeader.OnlyOneSection
        elif first:
            opt.position = (
                QtWidgets.QStyleOptionHeader.End
                if self.isRightToLeft()
                else QtWidgets.QStyleOptionHeader.Beginning
            )
        elif last:
            opt.position = (
                QtWidgets.QStyleOptionHeader.Beginning
                if self.isRightToLeft()
                else QtWidgets.QStyleOptionHeader.End
            )
        else:
            opt.position = QtWidgets.QStyleOptionHeader.Middle

        # Selection
        if self.orientation() == QtCore.Qt.Horizontal:
            previous_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual - 1), root
            )
            next_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual + 1), root
            )
        else:
            previous_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual - 1), root
            )
            next_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual + 1), root
            )
        if previous_selected and next_selected:
            opt.selectedPosition = (
                QtWidgets.QStyleOptionHeader.NextAndPreviousAreSelected
            )
        elif previous_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.PreviousIsSelected
        elif next_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NextIsSelected
        else:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NotAdjacent

        return opt

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
            elif self._positioning == self.Fill:
                return QtCore.QRect(
                    self.sectionViewportPosition(logical_index),
                    0,
                    self.sectionSize(logical_index),
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
            elif self._positioning == self.Fill:
                return QtCore.QRect(
                    0,
                    self.sectionViewportPosition(logical_index) + self.MARGIN,
                    self.width(),
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

    def widget_at(self, pos):
        logical_index = self.logicalIndexAt(pos)
        rect = self.get_widget_geometry(logical_index)
        if rect.contains(pos):
            return logical_index
        return -1

    def on_close_editor(self):
        self.finish_editing(accept_changes=False)

    def on_commit_data(self):
        self.finish_editing()

    @contextlib.contextmanager
    def _blocked_clickable(self, pos):
        # Prevent interaction with the widget region from triggering a
        # section click, otherwise it will be sorted (if sorting is
        # enabled). Note: setSortIndicator is not virtual so overriding
        # it explicitly is not possible
        clickable = self.sectionsClickable()
        logical_index = self.widget_at(pos)
        if logical_index != -1:
            self.setSectionsClickable(False)
        yield logical_index
        if self.sectionsClickable() != clickable:
            self.setSectionsClickable(clickable)

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
        if self._editing_index >= 0:
            if is_next:
                offset = 1
                focus_reason = QtCore.Qt.TabFocusReason
            else:
                offset = -1
                focus_reason = QtCore.Qt.BacktabFocusReason

            # Walk through the sections until the next editable section is found
            section = self._editing_index
            while True:
                section = (section + offset) % self.count()
                # If cycled back around to the same index, do nothing
                if section == self._editing_index:
                    self.finish_editing()
                    return False

                if (
                    self.model().headerData(
                        section, self.orientation(), HeaderRole.EditableRole
                    )
                    is not False
                ):
                    break

            self.edit_section(section, focus_reason=focus_reason)
        return True

    def headerDataChanged(self, orientation, first, last):
        # type: (QtCore.Qt.Orientation, int, int) -> None
        for i in range(first, last + 1):
            self.updateSection(i)

    def mousePressEvent(self, event):
        with self._blocked_clickable(event.pos()):
            super(EditableHeaderView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        with self._blocked_clickable(event.pos()) as logical_index:
            if logical_index != -1:
                if event.button() == QtCore.Qt.LeftButton:
                    self.edit_section(logical_index)
                elif event.button() == QtCore.Qt.MiddleButton:
                    self.clear_section(logical_index)
            super(EditableHeaderView, self).mouseReleaseEvent(event)

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        # Render the filter widget in the header widget rect

        opt = self.get_section_style_option(logical_index)
        opt.rect = self.get_widget_geometry(logical_index)

        painter.save()
        delegate = self.item_delegate_for_section(logical_index)
        delegate.paint(painter, opt, self.header_index(logical_index))
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
            width = size.width() * 2
            height = size.height()
        elif self._positioning == self.Below:
            width = size.width()
            height = size.height() * 2
        elif self._positioning == self.Fill:
            width = size.width()
            height = size.height()
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


class HeaderFilterProxy(QtCore.QSortFilterProxyModel):
    MatchExactly = 1
    MatchContains = 2
    MatchStarts = 3

    def __init__(self, parent=None):
        super(HeaderFilterProxy, self).__init__(parent)
        self._filters = {QtCore.Qt.Horizontal: [], QtCore.Qt.Vertical: []}
        self._default_filter_type = self.MatchContains

        self.headerDataChanged.connect(self.on_header_data_changed)

    @property
    def default_filter_type(self):
        return self._default_filter_type

    @default_filter_type.setter
    def default_filter_type(self, value):
        if value not in (self.MatchStarts, self.MatchContains, self.MatchExactly):
            raise ValueError("Unknown filter type: {}".format(value))
        self._default_filter_type = value

    def setSourceModel(self, model):
        # Must connect source model's signals otherwise the proxy's filtering
        # will modify the filters
        curr_model = self.sourceModel()
        if curr_model is not None:
            curr_model.rowsRemoved.disconnect(self.on_rows_removed)
            curr_model.rowsInserted.disconnect(self.on_rows_inserted)
            curr_model.columnsInserted.disconnect(self.on_columns_inserted)
            curr_model.columnsRemoved.disconnect(self.on_columns_removed)

        super(HeaderFilterProxy, self).setSourceModel(model)
        self._filters = {
            QtCore.Qt.Horizontal: [""] * model.columnCount(),
            QtCore.Qt.Vertical: [""] * model.rowCount(),
        }
        curr_model = self.sourceModel()
        if curr_model is not None:
            self.sourceModel().rowsRemoved.connect(self.on_rows_removed)
            self.sourceModel().rowsInserted.connect(self.on_rows_inserted)
            self.sourceModel().columnsInserted.connect(self.on_columns_inserted)
            self.sourceModel().columnsRemoved.connect(self.on_columns_removed)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == HeaderRole.EditRole:
            return self._filters[orientation][section]
        return super(HeaderFilterProxy, self).headerData(section, orientation, role)

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.DisplayRole):
        if role == HeaderRole.EditRole:
            value = str(value)
            string_list = self._filters[orientation]
            if string_list[section] != value:
                string_list[section] = value
                self.headerDataChanged.emit(orientation, section, section)
                return True
        return super(HeaderFilterProxy, self).setHeaderData(section, orientation, role)

    def _matches_filter(self, cell_text, filter_string, filter_type, case_sensitivity):
        if case_sensitivity == QtCore.Qt.CaseInsensitive:
            cell_text = cell_text.lower()
            filter_string = filter_string.lower()

        if filter_type == self.MatchExactly:
            return filter_string == cell_text
        elif filter_type == self.MatchContains:
            return filter_string in cell_text
        elif filter_type == self.MatchStarts:
            return cell_text.startswith(filter_string)
        else:
            raise ValueError("Unknown filter type: {}".format(filter_type))

    def filterAcceptsColumn(self, column, index):
        source_model = self.sourceModel()
        source_index = self.mapToSource(index)
        for row, filter_text in enumerate(self._filters[QtCore.Qt.Vertical]):
            if not filter_text:
                continue
            filter_type = (
                self.headerData(row, QtCore.Qt.Vertical, HeaderRole.FilterTypeRole)
                or self._default_filter_type
            )
            child_index = source_model.index(row, column, source_index)
            cell_text = str(child_index.data(QtCore.Qt.DisplayRole))
            case_sensitivity = self.headerData(row, QtCore.Qt.Vertical, HeaderRole.CaseSensitivityRole)
            if case_sensitivity is None:
                case_sensitivity = self.filterCaseSensitivity()
            if not self._matches_filter(cell_text, filter_text, filter_type, case_sensitivity):
                return False

        return True

    def filterAcceptsRow(self, row, index):
        source_model = self.sourceModel()
        source_index = self.mapToSource(index)
        for column, filter_text in enumerate(self._filters[QtCore.Qt.Horizontal]):
            if not filter_text:
                continue
            filter_type = (
                self.headerData(column, QtCore.Qt.Horizontal, HeaderRole.FilterTypeRole)
                or self._default_filter_type
            )
            child_index = source_model.index(row, column, source_index)
            cell_text = str(child_index.data(QtCore.Qt.DisplayRole))
            case_sensitivity = self.headerData(column, QtCore.Qt.Horizontal, HeaderRole.CaseSensitivityRole)
            if case_sensitivity is None:
                case_sensitivity = self.filterCaseSensitivity()
            if not self._matches_filter(cell_text, filter_text, filter_type, case_sensitivity):
                return False

        return True

    def on_header_data_changed(self, orientation, first, last):
        self.invalidateFilter()

    def on_columns_inserted(self, parent, first, last):
        self._filters[QtCore.Qt.Vertical][first:first] = [""] * (1 + last - first)

    def on_columns_removed(self, parent, first, last):
        del self._filters[QtCore.Qt.Vertical][first : last + 1]

    def on_rows_inserted(self, parent, first, last):
        self._filters[QtCore.Qt.Horizontal][first:first] = [""] * (1 + last - first)

    def on_rows_removed(self, parent, first, last):
        del self._filters[QtCore.Qt.Horizontal][first : last + 1]


class TableFilterView(QtWidgets.QTableView):
    def __init__(self, parent=None, model=None, horizontal=True, vertical=False):
        super(TableFilterView, self).__init__(parent)
        self._proxy = HeaderFilterProxy()
        self.setModel(self._proxy)

        if horizontal:
            h_header = EditableHeaderView(QtCore.Qt.Horizontal)
            self.setHorizontalHeader(h_header)

        if vertical:
            v_header = EditableHeaderView(QtCore.Qt.Vertical)
            self.setVerticalHeader(v_header)

        if model is not None:
            self.set_source_model(model)

    def default_filter_type(self):
        return self._proxy.default_filter_type

    def filter_case_sensitivity(self):
        return self._proxy.filterCaseSensitivity()

    def set_default_filter_type(self, filter_type):
        self._proxy.default_filter_type = filter_type

    def set_filter_case_sensitivity(self, sensitivity):
        self._proxy.setFilterCaseSensitivity(sensitivity)

    def set_horizontal_delegate(self, delegate):
        self.horizontalHeader().setItemDelegate(delegate)

    def set_vertical_delegate(self, delegate):
        self.verticalHeader().setItemDelegate(delegate)

    def set_horizontal_secton_delegate(self, section, delegate):
        self.horizontalHeader().set_item_delegate_for_section(section, delegate)

    def set_vertical_section_delegate(self, section, delegate):
        self.verticalHeader().set_item_delegate_for_section(section, delegate)

    def set_source_model(self, model):
        self._proxy.setSourceModel(model)

    def source_model(self):
        return self._proxy.sourceModel()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    class ExampleModel(QtCore.QAbstractItemModel):
        columns = ("one", "two", "three")

        def __init__(self, parent=None):
            # type: (QtWidgets.QWidget) -> None
            super(ExampleModel, self).__init__(parent)
            self._data = [
                ["1", "2", "3"],
                ["abc", "def", "ghi"],
                ["def", "ghi", "abc"],
                ["ghi", "abc", "def"],
                ["ONE", "TWO", "THREE"],
            ]

        def columnCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return 3

        def data(self, index, role=QtCore.Qt.DisplayRole):
            # type: (QtCore.QModelIndex, int) -> object
            if not index.isValid():
                return
            if role == QtCore.Qt.DisplayRole:
                return self._data[index.row()][index.column()]

        def flags(self, index):
            # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
            # type: (int, QtCore.Qt.Orientation, int) -> object
            if orientation == QtCore.Qt.Vertical:
                return
            if role == QtCore.Qt.DisplayRole:
                return self.columns[section]
            # elif role == HeaderRole.EditableRole:
            #     return section != 0
            elif role == HeaderRole.ChoicesRole:
                return ["", "1", "2", "3", "b", "e", "h"]
            elif role == HeaderRole.BackgroundColorRole and section != 0:
                return QtGui.QColor("red")
            elif role == HeaderRole.FilterTypeRole:
                if section == 0:
                    return HeaderFilterProxy.MatchExactly
                elif section == 1:
                    return HeaderFilterProxy.MatchContains
                elif section == 2:
                    return HeaderFilterProxy.MatchStarts
            elif role == HeaderRole.CaseSensitivityRole:
                if section == 0:
                    return QtCore.Qt.CaseInsensitive
                elif section == 1:
                    return QtCore.Qt.CaseInsensitive
                elif section == 2:
                    return QtCore.Qt.CaseSensitive

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column)

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self._data)

    model = ExampleModel()

    def debug(*args, **kwargs):
        print(args, kwargs)

    model.headerDataChanged.connect(debug)

    view = TableFilterView(model=model)
    combo_delegate = ComboHeaderDelegate(view)
    # view.set_horizontal_secton_delegate(1, combo_delegate)
    view.show()
    view.set_filter_case_sensitivity(QtCore.Qt.CaseInsensitive)

    app.exec_()
    sys.exit()
