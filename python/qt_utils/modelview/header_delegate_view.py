from PySide2 import QtCore, QtGui, QtWidgets


class HeaderModelIndex(object):
    def __init__(self, orientation, section=-1, model=None):
        # type: (int, int, QtCore.QAbstractItemModel) -> None
        self._orientation = orientation
        self._section = section
        self._model = model

    def __lt__(self, other):
        return self._section < other.section()

    def __eq__(self, other):
        if not isinstance(other, HeaderModelIndex):
            return False
        return (self._orientation == other.orientation() and
                self._section == other.section() and
                self._model == other.model())

    def data(self, role=QtCore.Qt.DisplayRole):
        if self._model is None:
            return
        return self._model.headerData(self._section, self._orientation, role)

    def isValid(self):
        # type: () -> bool
        return self._model is not None and self._section >= 0

    def model(self):
        # type: () -> QtCore.QAbstractItemModel
        return self._model

    def orientation(self):
        # type: () -> int
        return self._orientation

    def section(self):
        # type: () -> int
        return self._section

    def sibling(self, section):
        # type: (int) -> HeaderModelIndex
        return HeaderModelIndex(self._orientation, section, self._model)


class HeaderItemDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        # type: (QtWidgets.QWidget, QtGui.QStyleOptionHeader, HeaderModelIndex) -> QtWidgets.QWidget
        return QtWidgets.QLineEdit(parent)

    def paint(self, painter, option, index):
        # type: (QtGui.QPainter, QtGui.QStyleOptionHeader, HeaderModelIndex) -> None
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_Header, option, painter)

    def setEditorData(self, editor, index):
        # type: (QtWidgets.QWidget, HeaderModelIndex) -> None
        editor.setText(index.data())

    def setModelData(self, editor, model, index):
        # type: (QtWidgets.QWidget, QtCore.QAbstractItemModel, HeaderModelIndex) -> None
        model.setHeaderData(index.section(), index.orientation(), editor.text(), QtCore.Qt.EditRole)

    def sizeHint(self, option, index):
        # type: (QtGui.QStyleOptionHeader, HeaderModelIndex) -> None
        return QtWidgets.QLineEdit().sizeHint()

    def updateEditorGeometry(self, editor, option, index):
        # type: (QtWidgets.QWidget, QtCore.QAbstractItemModel, HeaderModelIndex) -> QtWidgets.QWidget
        # TODO: Check what this does and how it should be handled...
        pass


class HeaderDelegateView(QtWidgets.QHeaderView):
    def __init__(self, orientation, parent=None):
        super(HeaderDelegateView, self).__init__(orientation, parent)
        self._editors = {}

        self.setSectionsClickable(True)
        self.setHighlightSections(True)

        self.sectionDoubleClicked.connect(self.edit)

    def delegateForIndex(self, index):
        # type: (int) -> HeaderItemDelegate|None
        method = (self.itemDelegateForColumn
                  if self.orientation() == QtCore.Qt.Horizontal else
                  self.itemDelegateForRow)
        return method(index) or self.itemDelegate()

    def edit(self, index):  # trigger, event):
        # type: (int) -> bool
        if index < 0 or index >= self.count():
            return False
        if not self.model().headerData(index, self.orientation(), QtCore.Qt.EditRole):
            return False
        options = self.get_section_style_option(index)
        options.state |= QtWidgets.QStyle.State_HasFocus
        editor = self.editor(index, options)
        if editor is None:
            return False
        # TODO: Figure out how to properly close the delegate when done editing
        # Working, but doesn't hide when done. Look up how it's normally used
        rect = self.sectionRect(index)
        editor.setGeometry(rect)
        self.setState(self.EditingState)  # Don't know what this does
        editor.show()
        editor.setFocus()
        return True

    def editor(self, logical_index, options):
        # type: (int, QtWidgets.QStyleOptionHeader) -> HeaderItemDelegate|None
        w = self._editors.get(logical_index)
        if not w:
            delegate = self.delegateForIndex(logical_index)
            if not delegate:
                return
            model_index = HeaderModelIndex(self.orientation(), logical_index, self.model())
            w = delegate.createEditor(self.viewport(), options, model_index)
            if w:
                w.installEventFilter(delegate)
                delegate.destroyed.connect(self.editorDestroyed)
                delegate.updateEditorGeometry(w, options, model_index)
                delegate.setEditorData(w, model_index)
                self._editors[logical_index] = w

                # Sets focus order for widgets
                if w.parent() == self.viewport():
                    QtWidgets.QWidget.setTabOrder(self, w)

                # No idea what this is doing. Is it necessary?
                focusWidget = w
                while focusWidget.focusProxy():
                    focusWidget = focusWidget.focusProxy()

                if isinstance(focusWidget, (QtWidgets.QLineEdit,
                                            QtWidgets.QSpinBox,
                                            QtWidgets.QDoubleSpinBox)):
                    focusWidget.selectAll()

        return w

    def sectionSizeHint(self, logical_index):
        delegate = self.delegateForIndex(logical_index)
        if delegate is None:
            return super(HeaderDelegateView, self).sectionSizeHint(logical_index)
        return delegate.sizeHint().width()

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        if not rect.isValid():
            return

        painter.save()

        opt = self.get_section_style_option(logical_index)
        opt.rect = rect

        # Update the state based on the current mouse state in relation to the
        # section rect
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        if opt.rect.contains(mouse_pos):
            if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
                opt.state |= QtWidgets.QStyle.State_Sunken
            else:
                opt.state |= QtWidgets.QStyle.State_MouseOver

        # I don't think this is ever needed here, the widget will draw itself
        # in the right location, this just needs to draw the non-widget state
        # editor = self.editor(logical_index, opt)

        # Check if it has a delegate and if it defines a paint method
        delegate = self.delegateForIndex(logical_index)
        if delegate is not None:
            print('Painting delegate')
            delegate.paint(painter, opt, HeaderModelIndex(self.orientation(), logical_index, self.model()))
        else:
            # style = self.style()
            # style.drawControl(QtWidgets.QStyle.CE_HeaderSection, opt, painter, self)
            # painter.setBrush(opt.palette.background())
            # painter.drawRect(rect)
            # style.drawControl(QtWidgets.QStyle.CE_HeaderLabel, opt, painter, self)
            #
            # # WIP: sortIndicator drawing
            # if opt.sortIndicator:
            #     opt.rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderArrow, opt)
            #     style.proxy().drawPrimitive(QtWidgets.QStyle.PE_IndicatorHeaderArrow, opt, painter)

            self.style().drawControl(QtWidgets.QStyle.CE_Header, opt, painter, self)

        painter.restore()

    def sectionRect(self, logical_index):
        # type: (int) -> QtCore.QRect
        # Accumulate the offset from the
        pos = self.sectionViewportPosition(logical_index)
        if self.orientation() == QtCore.Qt.Horizontal:
            return QtCore.QRect(pos, 0, self.sectionSize(logical_index), self.height())
        else:
            return QtCore.QRect(0, pos, self.width(), self.sectionSize(logical_index))

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
        header_arrow_alignment = style.styleHint(QtWidgets.QStyle.SH_Header_ArrowAlignment, opt, self)
        is_header_arrow_on_the_side = header_arrow_alignment & QtCore.Qt.AlignVCenter
        if (self.isSortIndicatorShown()
                and self.sortIndicatorSection() == logical_index
                and is_header_arrow_on_the_side):
            margin += style.pixelMetric(QtWidgets.QStyle.PM_HeaderMarkSize, opt, self)

        # Icon
        opt.iconAlignment = QtCore.Qt.AlignVCenter
        icon = model.headerData(logical_index, orientation, QtCore.Qt.DecorationRole)
        if icon and not icon.isNull():
            opt.icon = icon
            margin += (style.pixelMetric(QtWidgets.QStyle.PM_SmallIconSize, opt, self) +
                       style.pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, self))

        # Text
        text_alignment = model.headerData(logical_index, orientation,
                                          QtCore.Qt.TextAlignmentRole)
        opt.textAlignment = text_alignment or QtCore.Qt.AlignCenter  # d.defaultAlignment
        opt.text = model.headerData(logical_index, orientation, QtCore.Qt.DisplayRole)
        if self.textElideMode() != QtCore.Qt.ElideNone:
            text_rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderLabel, opt, self)
            opt.text = opt.fontMetrics.elidedText(opt.text, self.textElideMode(),
                                                  text_rect.width() - margin)

        # Brushes
        background_brush = model.headerData(logical_index, orientation, QtCore.Qt.BackgroundRole)
        if background_brush is not None:
            brush = QtGui.QBrush(background_brush)
            opt.palette.setBrush(QtGui.QPalette.Button, brush)
            opt.palette.setBrush(QtGui.QPalette.Window, brush)

        foreground_brush = model.headerData(logical_index, orientation, QtCore.Qt.ForegroundRole)
        if foreground_brush is not None:
            opt.palette.setBrush(QtGui.QPalette.ButtonText, QtGui.QBrush(foreground_brush))

        # Header section attributes
        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logical_index:
            opt.sortIndicator = (QtWidgets.QStyleOptionHeader.SortDown
                                 if (self.sortIndicatorOrder() == QtCore.Qt.AscendingOrder) else
                                 QtWidgets.QStyleOptionHeader.SortUp)
        opt.section = logical_index
        opt.orientation = orientation

        # Position
        visual = self.visualIndex(logical_index)
        first = self.logicalIndex(0) == logical_index
        last = self.logicalIndex(self.count() - 1) == logical_index
        if first and last:
            opt.position = QtWidgets.QStyleOptionHeader.OnlyOneSection
        elif first:
            opt.position = (QtWidgets.QStyleOptionHeader.End
                            if self.isRightToLeft() else
                            QtWidgets.QStyleOptionHeader.Beginning)
        elif last:
            opt.position = (QtWidgets.QStyleOptionHeader.Beginning
                            if self.isRightToLeft() else
                            QtWidgets.QStyleOptionHeader.End)
        else:
            opt.position = QtWidgets.QStyleOptionHeader.Middle

        # Selection
        if self.orientation() == QtCore.Qt.Horizontal:
            previous_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual - 1), root)
            next_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual + 1), root)
        else:
            previous_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual - 1), root)
            next_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual + 1), root)
        if previous_selected and next_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NextAndPreviousAreSelected
        elif previous_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.PreviousIsSelected
        elif next_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NextIsSelected
        else:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NotAdjacent

        return opt


# class MetaHeaderView(QtWidgets.QHeaderView):
#
#     def __init__(self, orientation, parent=None):
#         super(MetaHeaderView, self).__init__(orientation, parent)
#         self.setSectionsMovable(True)
#         self.setSectionsClickable(True)
#         # This block sets up the edit line by making setting the parent
#         # to the Headers Viewport.
#         self.line = QtWidgets.QLineEdit(parent=self.viewport())  # Create
#         self.line.setAlignment(QtCore.Qt.AlignTop)  # Set the Alignmnet
#         self.line.setHidden(True)  # Hide it till its needed
#         # This is needed because I am having a werid issue that I believe has
#         # to do with it losing focus after editing is done.
#         self.line.blockSignals(True)
#         self.sectionedit = 0
#         # Connects to double click
#         self.sectionDoubleClicked.connect(self.editHeader)
#         self.line.editingFinished.connect(self.doneEditing)
#
#     def doneEditing(self):
#         # This block signals needs to happen first otherwise I have lose focus
#         # problems again when there are no rows
#         self.line.blockSignals(True)
#         self.line.setHidden(True)
#         # oldname = self.model().dataset.field(self.sectionedit)
#         # newname = str(self.line.text())
#         # self.model().dataset.changeFieldName(oldname, newname)
#         self.line.setText('')
#         self.setCurrentIndex(QtCore.QModelIndex())
#
#     def editHeader(self, section):
#         # This block sets up the geometry for the line edit
#         edit_geometry = self.line.geometry()
#         edit_geometry.setWidth(self.sectionSize(section))
#         edit_geometry.moveLeft(self.sectionViewportPosition(section))
#         self.line.setGeometry(edit_geometry)
#
#         # self.line.setText(self.model().dataset.field(section).name)
#         self.line.setHidden(False)  # Make it visiable
#         self.line.blockSignals(False)  # Let it send signals
#         self.line.setFocus()
#         self.line.selectAll()
#         self.sectionedit = section


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    model = QtGui.QStandardItemModel()
    model.setHorizontalHeaderLabels([
        'name',
        'age',
        'gender',
        'surname',
    ])
    model.insertRow(0, [
        QtGui.QStandardItem('ray'),
        QtGui.QStandardItem('30'),
        QtGui.QStandardItem('male'),
        QtGui.QStandardItem('barrett'),
    ])
    model.insertRow(1, [
        QtGui.QStandardItem('emma'),
        QtGui.QStandardItem('30'),
        QtGui.QStandardItem('female'),
        QtGui.QStandardItem('dunlop'),
    ])

    view = QtWidgets.QTableView()
    header = HeaderDelegateView(QtCore.Qt.Horizontal)
    delegate = HeaderItemDelegate()
    header.setItemDelegate(delegate)
    view.setHorizontalHeader(header)
    view.setModel(model)
    view.show()

    # print(header.receivers(QtCore.SIGNAL("editorDestroyed()")))

    app.exec_()
    sys.exit()
