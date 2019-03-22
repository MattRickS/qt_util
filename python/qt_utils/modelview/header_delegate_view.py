from PySide2 import QtCore, QtGui, QtWidgets


def qSmartMinSizeWidget(widget):
    return qSmartMinSize(
        widget.sizeHint(),
        widget.minimumSizeHint(),
        widget.minimumSize(),
        widget.maximumSize(),
        widget.sizePolicy(),
    )


def qSmartMinSize(sizeHint, minSizeHint, minSize, maxSize, sizePolicy):
    s = QtCore.QSize(0, 0)
    if sizePolicy.horizontalPolicy() != QtWidgets.QSizePolicy.Ignored:
        if sizePolicy.horizontalPolicy() & QtWidgets.QSizePolicy.ShrinkFlag:
            s.setWidth(minSizeHint.width())
        else:
            s.setWidth(max(sizeHint.width(), minSizeHint.width()))
    if sizePolicy.verticalPolicy() != QtWidgets.QSizePolicy.Ignored:
        if sizePolicy.verticalPolicy() & QtWidgets.QSizePolicy.ShrinkFlag:
            s.setHeight(minSizeHint.height())
        else:
            s.setHeight(max(sizeHint.height(), minSizeHint.height()))

    s = s.boundedTo(maxSize)
    if minSize.width() > 0:
        s.setWidth(minSize.width())
    if minSize.height() > 0:
        s.setHeight(minSize.height())
    return s.expandedTo(QtCore.QSize(0, 0))


def qFuzzyCompare(p1, p2):
    return abs(p1 - p2) * 1000000000000.0 <= min(abs(p1), abs(p2))


class PainterStateGuard(object):
    def __init__(self, p):
        self.m_painter = p
        self.m_level = 0

    def __del__(self):
        while self.m_level > 0:
            self.m_level -= 1
            self.m_painter.restore()

    def save(self):
        self.m_painter.save()
        self.m_level += 1

    def restore(self):
        self.m_painter.restore()
        self.m_level -= 1


def qDrawShadePanel(p, x, y, w, h, pal, sunken, lineWidth, fill):
    # type: (QtGui.QPainter, int, int, int, int, QtGui.QPalette, bool, int, QtGui.QBrush) -> None
    if w == 0 or h == 0:
        return
    if w < 0 or h < 0 or lineWidth < 0:
        print("qDrawShadePanel: Invalid parameters")

    painterGuard = PainterStateGuard(p)
    # devicePixelRatioF() is causing segmentation faults
    devicePixelRatio = 1.0  # p.device().devicePixelRatioF()
    if not qFuzzyCompare(devicePixelRatio, 1.0):
        painterGuard.save()
        inverseScale = 1.0 / devicePixelRatio
        p.scale(inverseScale, inverseScale)
        x = round(devicePixelRatio * x)
        y = round(devicePixelRatio * y)
        w = round(devicePixelRatio * w)
        h = round(devicePixelRatio * h)
        lineWidth = round(devicePixelRatio * lineWidth)

    shade = pal.dark().color()
    light = pal.light().color()
    if fill:
        if fill.color() == shade:
            shade = pal.shadow().color()
        if fill.color() == light:
            light = pal.midlight().color()

    oldPen = p.pen()  # save pen
    lines = []
    if sunken:
        p.setPen(shade)
    else:
        p.setPen(light)
    x1, y1, x2, y2 = x, y, x + w - 2, y

    for i in range(lineWidth):  # top shadow
        y1 += 1
        x2 -= 1
        y2 += 1
        lines.append(QtCore.QLineF(x1, y1, x2, y2))

    x2 = x1
    y1 = y + h - 2
    for i in range(lineWidth):  # left shadow
        x1 += 1
        x2 += 1
        y2 -= 1
        lines.append(QtCore.QLineF(x1, y1, x2, y2))

    p.drawLines(lines)
    lines.clear()
    if sunken:
        p.setPen(light)
    else:
        p.setPen(shade)

    x1 = x
    y1 = y2 = y + h - 1
    x2 = x + w - 1
    for i in range(lineWidth):  # bottom shadow
        x1 += 1
        y1 -= 1
        y2 -= 1
        lines.append(QtCore.QLineF(x1, y1, x2, y2))

    x1 = x2
    y1 = y
    y2 = y + h - lineWidth - 1
    for i in range(lineWidth):  # right shadow
        x1 -= 1
        y1 += 1
        x2 -= 1
        lines.append(QtCore.QLineF(x1, y1, x2, y2))

    p.drawLines(lines)
    if fill:  # fill with fill color
        p.fillRect(x + lineWidth, y + lineWidth, w - lineWidth * 2, h - lineWidth * 2, fill)
    p.setPen(oldPen)  # restore pen


def qt_getWindow(widget):
    return widget.window().windowHandle() if widget else 0


def _draw_header_section(opt, painter):
    qDrawShadePanel(
        painter,
        opt.rect.x(),
        opt.rect.y(),
        opt.rect.width(),
        opt.rect.height(),
        opt.palette,
        opt.state & QtWidgets.QStyle.State_Sunken,
        1,
        opt.palette.brush(QtGui.QPalette.Button)
    )


def _draw_header_label(opt, painter, widget):
    rect = opt.rect
    if not opt.icon.isNull():
        iconExtent = widget.style().proxy().pixelMetric(QtWidgets.QStyle.PM_SmallIconSize)
        pixmap = opt.icon.pixmap(
            qt_getWindow(widget),
            QtCore.QSize(iconExtent, iconExtent),
            QtGui.QIcon.Normal if (opt.state & QtWidgets.QStyle.State_Enabled) else QtGui.QIcon.Disabled
        )
        pixw = pixmap.width() / pixmap.devicePixelRatio()
        aligned = widget.style().alignedRect(
            opt.direction,
            opt.iconAlignment,  # QFlag(header.iconAlignment),
            pixmap.size() / pixmap.devicePixelRatio(),
            rect
        )
        inter = aligned.intersected(rect)
        painter.drawPixmap(
            inter.x(),
            inter.y(),
            pixmap,
            inter.x() - aligned.x(),
            inter.y() - aligned.y(),
            aligned.width() * pixmap.devicePixelRatio(),
            pixmap.height() * pixmap.devicePixelRatio()
        )
        margin = widget.style().proxy().pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, widget)
        if opt.direction == QtCore.Qt.LeftToRight:
            rect.setLeft(rect.left() + pixw + margin)
        else:
            rect.setRight(rect.right() - pixw - margin)

    if opt.state & QtWidgets.QStyle.State_On:
        fnt = painter.font()
        fnt.setBold(True)
        painter.setFont(fnt)

    widget.style().proxy().drawItemText(
        painter,
        rect,
        opt.textAlignment,
        opt.palette,
        (opt.state & QtWidgets.QStyle.State_Enabled),
        opt.text,
        QtGui.QPalette.ButtonText
    )


def _draw_header(opt, painter, widget):
        # type: (QtWidgets.QStyleOptionHeader, QtGui.QPainter, QtWidgets.QHeaderView) -> None
        print('Draw header')
        # PySide does not correctly handle the python values set on the
        # QStyleOptionHeader, so they are lost when cast to/from QStyleOption in
        # standard QStyle draw commands. To ensure correct behaviour, handle the
        # paint methods ourselves
        clipRegion = painter.clipRegion()
        painter.setClipRect(opt.rect)

        # self.style().proxy().drawControl(
        #     QtWidgets.QStyle.CE_HeaderSection, opt, painter, self
        # )
        _draw_header_section(opt, painter)

        subopt = QtWidgets.QStyleOptionHeader(opt)
        subopt.rect = widget.style().proxy().subElementRect(
            QtWidgets.QStyle.SE_HeaderLabel, subopt, widget
        )

        if subopt.rect.isValid():
            # self.style().proxy().drawControl(
            #     QtWidgets.QStyle.CE_HeaderLabel, subopt, painter, self
            # )
            _draw_header_label(opt, painter, widget)

        if opt.sortIndicator != QtWidgets.QStyleOptionHeader.SortIndicator(0):
            subopt.rect = widget.style().proxy().subElementRect(
                QtWidgets.QStyle.SE_HeaderArrow, opt, widget
            )
            widget.style().proxy().drawPrimitive(
                QtWidgets.QStyle.PE_IndicatorHeaderArrow, subopt, painter, widget
            )

        painter.setClipRegion(clipRegion)


class HeaderModelIndex(object):
    def __init__(self, orientation, section=-1, model=None, view=None):
        # type: (int, int, QtCore.QAbstractItemModel, QtWidgets.QHeaderView) -> None
        self._orientation = orientation
        self._section = section
        self._model = model
        self._view = view

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

    def view(self):
        return self._view


class HeaderItemDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        # type: (QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> None
        # TODO: index NOT ON QStyleOptionHeader
        # option.index = index

        value = index.data(QtCore.Qt.FontRole)
        if value is not None:
            # TODO: font NOT ON QStyleOptionHeader
            font = QtGui.QFont(value).resolve(option.font)
            # option.font = font
            option.fontMetrics = QtGui.QFontMetrics(font)

        # value = index.data(QtCore.Qt.TextAlignmentRole)
        # if value is not None:
        #     # TODO: displayAlignment NOT ON QStyleOptionHeader
        #     option.displayAlignment = QtCore.Qt.Alignment(value)

        value = index.data(QtCore.Qt.ForegroundRole)
        if value is not None:
            option.palette.setBrush(QtGui.QPalette.Text, QtGui.QBrush(value))

        # value = index.data(QtCore.Qt.CheckStateRole)
        # if value is not None:
        #     # TODO: features, checkState NOT ON QStyleOptionHeader
        #     option.features |= QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        #     option.checkState = QtCore.Qt.CheckState(value)

        value = index.data(QtCore.Qt.DecorationRole)
        if value is not None:
            # TODO: features, decorationSize NOT ON QStyleOptionHeader
            # option.features |= QtWidgets.QStyleOptionViewItem.HasDecoration
            if isinstance(value, QtGui.QIcon):
                option.icon = value
                # if not (option.state & QtWidgets.QStyle.State_Enabled):
                #     mode = QtGui.QIcon.Disabled
                # elif option.state & QtWidgets.QStyle.State_Selected:
                #     mode = QtGui.QIcon.Selected
                # else:
                #     mode = QtGui.QIcon.Normal
                # state = QtGui.QIcon.On if option.state & QtWidgets.QStyle.State_Open else QtGui.QIcon.Off
                # actualSize = option.icon.actualSize(option.decorationSize, mode, state)
                # # For highdpi icons actualSize might be larger than decorationSize,
                # # which we don't want. Clamp it to decorationSize.
                # option.decorationSize = QtCore.QSize(
                #     min(option.decorationSize.width(), actualSize.width()),
                #     min(option.decorationSize.height(), actualSize.height())
                # )
            elif isinstance(value, QtGui.QColor):
                pixmap = QtGui.QPixmap(option.decorationSize)
                pixmap.fill(value)
                option.icon = QtGui.QIcon(pixmap)
            elif isinstance(value, QtGui.QImage):
                option.icon = QtGui.QIcon(QtGui.QPixmap.fromImage(value))
                # option.decorationSize = value.size() / value.devicePixelRatio()
            elif isinstance(value, QtGui.QPixmap):
                option.icon = QtGui.QIcon(value)
                # option.decorationSize = value.size() / value.devicePixelRatio()

        value = index.data(QtCore.Qt.DisplayRole)
        if value is not None:
            # TODO: features NOT ON QStyleOptionHeader
            # option.features |= QtWidgets.QStyleOptionViewItem.HasDisplay
            option.text = value  # self.displayText(value, option.locale)

        option.backgroundBrush = QtGui.QBrush(index.data(QtCore.Qt.BackgroundRole))
        # NOT SURE IF THIS IS ACCESSIBLE
        option.styleObject = None

    def createEditor(self, parent, option, index):
        # type: (QtWidgets.QWidget, QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> QtWidgets.QWidget
        if not index.isValid():
            return
        # TODO: Creates a widget, but it's deleted during the edit() method, probably because we're
        # not using the right signals/events to start the editing

        # factory = self.itemEditorFactory() or QtWidgets.QItemEditorFactory.defaultFactory()
        # edit_role = index.data(QtCore.Qt.EditRole)
        # print('Edit role:', edit_role)
        # if not isinstance(edit_role, int):
        #     edit_role = 30
        # return factory.createEditor(edit_role, parent)
        return QtWidgets.QLineEdit(parent)

    def destroyEditor(self, editor, index):
        editor.deleteLater()

    def editorEvent(self, event, option, index):
        # type: (QtCore.QEvent, QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> bool
        # TODO: Find calling methods, check what it should be doing, match to our custom data
        return super(HeaderItemDelegate, self).editorEvent(event, option, index)

    def paint(self, painter, option, index):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> None
        _draw_header(option, painter, index.view())

    def setEditorData(self, editor, index):
        # type: (QtWidgets.QWidget, HeaderModelIndex) -> None
        editor.setText(index.data())

    def setModelData(self, editor, model, index):
        # type: (QtWidgets.QWidget, QtCore.QAbstractItemModel, HeaderModelIndex) -> None
        model.setHeaderData(index.section(), index.orientation(), editor.text(), QtCore.Qt.EditRole)

    def sizeHint(self, option, index):
        # type: (QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> None
        return QtWidgets.QLineEdit().sizeHint()

    def updateEditorGeometry(self, editor, option, index):
        # type: (QtWidgets.QWidget, QtWidgets.QStyleOptionHeader, HeaderModelIndex) -> None
        # QStyledItemDelegate behaviour
        if not editor or not index.isValid():
            return

        # We're _supposed_ to use the style to find the correct rect for the region,
        # but we're probably going to want the whole header rect.
        # opt = QtWidgets.QStyleOptionHeader(option)
        # self.initStyleOption(opt, index)
        # if isinstance(editor, QtWidgets.QLineEdit):
        #     opt.showDecorationSelected = editor.style().styleHint(
        #         QtWidgets.QStyle.SH_ItemView_ShowDecorationSelected, None, editor)
        # else:
        #     opt.showDecorationSelected = True
        # geom = QtWidgets.QApplication.style().subElementRect(
        #     QtWidgets.QStyle.SE_HeaderLabel, opt
        # )
        geom = option.rect
        delta = qSmartMinSizeWidget(editor).width() - geom.width()
        if delta > 0:
            # we need to widen the geometry
            if editor.layoutDirection() == QtCore.Qt.RightToLeft:
                geom.adjust(-delta, 0, 0, 0)
            else:
                geom.adjust(0, 0, delta, 0)
        editor.setGeometry(geom)


class HeaderDelegateView(QtWidgets.QHeaderView):
    def __init__(self, orientation, parent=None):
        super(HeaderDelegateView, self).__init__(orientation, parent)
        self._editors = {}
        self.__currentlyCommittingEditor = None

        self.setSectionsClickable(True)
        self.setHighlightSections(True)

        self.sectionDoubleClicked.connect(self.edit)


    # TODO: Check if implementing the mouse events will trigger more correct behaviour
    # def mouseDoubleClickEvent(self, event):
    #     index = self.indexAt(event.pos()).column()
    #     if (index < 0 or self.count() <= index or
    #         not d.isIndexEnabled(index)
    #         or d.pressedIndex != index):
    #         me = QtCore.QEvent(QtCore.QEvent.MouseButtonPress,
    #                        event.localPos(), event.windowPos(), event.screenPos(),
    #                        event.button(), event.buttons(), event.modifiers(), event.source())
    #         self.mousePressEvent(me)
    #         return
    #
    #     self.doubleClicked(persistent)
    #     if ((event.button() == QtCore.Qt.LeftButton) and not self.edit(index, self.DoubleClicked, event)
    #         and not self.style().styleHint(QtWidgets.QStyle.SH_ItemView_ActivateItemOnSingleClick, 0, self)):
    #         self.activated.emit(index)

    def delegateForIndex(self, index):
        # type: (int) -> HeaderItemDelegate|None
        method = (self.itemDelegateForColumn
                  if self.orientation() == QtCore.Qt.Horizontal else
                  self.itemDelegateForRow)
        return method(index) or self.itemDelegate()

    def commitData(self, editor):
        if not editor or not self.itemDelegate() or self.__currentlyCommittingEditor:
            return
        index = self.indexForEditor(editor)
        if index is None:
            return
        self.__currentlyCommittingEditor = editor
        delegate = self.delegateForIndex(index)
        editor.removeEventFilter(delegate)
        index = HeaderModelIndex(self.orientation(), index, self.model())
        delegate.setModelData(editor, self.model(), index)
        editor.installEventFilter(delegate)
        self.__currentlyCommittingEditor = None

    # TODO: Is this required? It seems to work without it (ie, removeEditor is
    # called anyway)
    # /*!
    #     This function is called when the given \a editor has been destroyed.
    #     \sa closeEditor()
    # */
    # void QAbstractItemView::editorDestroyed(QObject *editor)
    # {
    #     Q_D(QAbstractItemView);
    #     QWidget *w = qobject_cast<QWidget*>(editor);
    #     d->removeEditor(w);
    #     d->persistent.remove(w);
    #     if (state() == EditingState)
    #         setState(NoState);
    # }

    def indexForEditor(self, editor):
        # type: (QtWidgets.QWidget) -> int|None
        # TODO: This should return a HeaderModelIndex and everything update accordingly
        for k, v in self._editors.items():
            if editor == v:
                return k

    def removeEditor(self, editor):
        # type: (QtWidgets.QWidget) -> None
        for k, v in self._editors.items():
            if editor == v:
                self._editors.pop(k)
                return

    def releaseEditor(self, editor, index=-1):
        if editor:
            # TODO: This errors, we mustn't have connected it - find out where it should have happened
            # editor.destroyed.disconnect(self.editorDestroyed)
            editor.removeEventFilter(self.itemDelegate())
            editor.hide()
            delegate = self.delegateForIndex(index)
            if delegate:
                delegate.destroyEditor(editor, index)
            else:
                editor.deleteLater()

    def selectionBehaviorFlags(self):
        behaviour = self.selectionBehavior()
        if behaviour == self.SelectRows:
            return QtCore.QItemSelectionModel.Rows
        elif behaviour == self.SelectColumns:
            return QtCore.QItemSelectionModel.Columns
        else:
            return QtCore.QItemSelectionModel.NoUpdate

    # TODO: I'm not calling this, so something from the C++ side is. Check what
    # so we can be sure the right hints are being sent - currently can't move
    # delegate
    def closeEditor(self, editor, hint):
        # Close the editor
        if editor:
            # TODO: Add persistent support
            isPersistent = False  # d.persistent.contains(editor)
            hadFocus = editor.hasFocus()
            index = self.indexForEditor(editor)
            if index is None:
                return  # the editor was not registered
            if not isPersistent:
                self.setState(self.NoState)
                editor.removeEventFilter(self.delegateForIndex(index))
                self.removeEditor(editor)
            if hadFocus:
                if self.focusPolicy() != QtCore.Qt.NoFocus:
                    self.setFocus()  # this will send a focusLost event to the editor
                else:
                    editor.clearFocus()
            # else:
            #     d.checkPersistentEditorFocus()
            ed = editor
            QtWidgets.QApplication.sendPostedEvents(editor, 0)
            editor = ed
            if not isPersistent and editor:
                self.releaseEditor(editor, index)

        # # The EndEditHint part
        # flags = QtCore.QItemSelectionModel.NoUpdate
        # if self.selectionMode() != self.NoSelection:
        #     flags = QtCore.QItemSelectionModel.ClearAndSelect | self.selectionBehaviorFlags()

        if hint == QtWidgets.QAbstractItemDelegate.EditNextItem:
            index = self.moveCursor(self.MoveNext, QtCore.Qt.NoModifier)
            if index.isValid():
                # TODO: orientation support
                self.edit(index.column())
                # persistent = QtCore.QPersistentModelIndex(index)
                # self.selectionModel().setCurrentIndex(persistent, flags)
                # # currentChanged signal would have already started editing
                # if (index.flags() & QtCore.Qt.ItemIsEditable
                #     and not (self.editTriggers() & QtWidgets.QAbstractItemView.CurrentChanged)):
                #     self.edit(persistent)
        elif hint == QtWidgets.QAbstractItemDelegate.EditPreviousItem:
            index = self.moveCursor(self.MovePrevious, QtCore.Qt.NoModifier)
            if index.isValid():
                # TODO: orientation support
                self.edit(index.column())
                # persistent = QtCore.QPersistentModelIndex(index)
                # d.selectionModel.setCurrentIndex(persistent, flags)
                # # currentChanged signal would have already started editing
                # if (index.flags() & QtCore.Qt.ItemIsEditable
                #     and not (self.editTriggers() & QtWidgets.QAbstractItemView.CurrentChanged)):
                #     self.edit(persistent)
        # TODO: I'm fairly certain these aren't supported here AT ALL
        elif hint == QtWidgets.QAbstractItemDelegate.SubmitModelCache:
            self.model().submit()
        elif hint == QtWidgets.QAbstractItemDelegate.RevertModelCache:
            self.model().revert()

    def openEditor(self, index, event=None):
        # type: (int, QtCore.QEvent) -> bool
        # In case this is being called somewhere we aren't overriding, convert
        # it to the logical index
        if isinstance(index, QtCore.QModelIndex):
            index = index.column()
        options = self.get_section_style_option(index)
        options.rect = self.sectionRect(index)
        # Use the index column for focus instead of the exact index
        options.state |= (QtWidgets.QStyle.State_HasFocus if index == self.currentIndex().column()
                          else QtWidgets.QStyle.State_None)
        w = self.editor(index, options)
        if w is None:
            return False
        self.setState(QtWidgets.QAbstractItemView.EditingState)
        w.show()
        w.setFocus()
        if event:
            QtWidgets.QApplication.sendEvent(w.focusProxy() or w, event)
        return True

    def edit(self, index, trigger=QtWidgets.QAbstractItemView.AllEditTriggers, event=None):
        # type: (int) -> bool
        # This is a very modified version of the original (see below). We don't
        # have access to the D-pointer to use the private timers, so we're
        # missing the nuances of user interaction, but this might be ok...
        # In case this is being called somewhere we aren't overriding, convert
        # it to the logical index
        if isinstance(index, QtCore.QModelIndex):
            index = index.column()
        if index < 0 or index >= self.count():
            return False
        if not self.model().headerData(index, self.orientation(), QtCore.Qt.EditRole):
            return False
        return self.openEditor(index, event)

        # if not index.isValid():
        #     return False
        #
        # w = None if d.persistent.isEmpty() else d.editorForIndex(index).widget.data()
        # if w is not None:
        #     if w.focusPolicy() == QtCore.Qt.NoFocus:
        #         return False
        #     w.setFocus()
        #     return True
        #
        # # Checks against existing timers to ensure editing is not accidentally triggered
        # if trigger == self.DoubleClicked:
        #     d.delayedEditing.stop()
        #     d.delayedAutoScroll.stop()
        # elif trigger == self.CurrentChanged:
        #     d.delayedEditing.stop()
        #
        # # Try sending the event to the delegate...?
        # if self.sendDelegateEvent(index, event):
        #     self.update(index)
        #     return True
        #
        # # save the previous trigger before updating
        # lastTrigger = d.lastTrigger
        # d.lastTrigger = trigger
        # if not d.shouldEdit(trigger, d.model().buddy(index)):
        #     return False
        # if d.delayedEditing.isActive():
        #     return False
        # # we will receive a mouseButtonReleaseEvent after a
        # # mouseDoubleClickEvent, so we need to check the previous trigger
        # if lastTrigger == self.DoubleClicked and trigger == self.SelectedClicked:
        #     return False
        # # we may get a double click event later
        # if trigger == self.SelectedClicked:
        #     d.delayedEditing.start(QtWidgets.QApplication.doubleClickInterval(), self)
        # else:
        #     d.openEditor(index, event if d.shouldForwardEvent(trigger, event) else 0)
        # return True

    # TODO: Check if this is being used, what should be calling it, etc...
    def sendDelegateEvent(self, index, event):
        # type: (int|QtCore.QModelIndex, QtCore.QEvent) -> bool
        if isinstance(index, QtCore.QModelIndex):
            index = index.column()
        options = self.get_section_style_option(index)
        options.rect = self.sectionRect(index)
        options.state |= QtWidgets.QStyle.State_HasFocus if index == self.currentIndex().column() else QtWidgets.QStyle.State_None
        delegate = self.delegateForIndex(index)
        return event and delegate and delegate.editorEvent(event, model, options, index)

    def editor(self, logical_index, options):
        # type: (int, QtWidgets.QStyleOptionHeader) -> QtWidgets.QWidget|None
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

        # TODO: Compare against the "correct" paintSection
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
            delegate.paint(painter,
                           opt,
                           HeaderModelIndex(self.orientation(),
                                            section=logical_index,
                                            model=self.model(),
                                            view=self)
                           )
        else:
            _draw_header(opt, painter, self)
            # self.style().drawControl(QtWidgets.QStyle.CE_Header, opt, painter, self)

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
        header_arrow_alignment = style.styleHint(QtWidgets.QStyle.SH_Header_ArrowAlignment, opt,
                                                 self)
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

    # TODO: Should these be implemented? requires custom index/model handling,
    # but don't seem to do anything if enabled in their current state. Check.

    # def shouldEdit(self, trigger, index):
    #     # type: (QtWidgets.QAbstractItemView.EditTrigger, QtCore.QModelIndex) -> bool
    #     if not index.isValid():
    #         return False
    #     flags = self.model().flags(index)
    #     if ((flags & QtCore.Qt.ItemIsEditable) == 0) or ((flags & QtCore.Qt.ItemIsEnabled) == 0):
    #         return False
    #     if self.state() == QtWidgets.QAbstractItemView.EditingState:
    #         return False
    #     if self.hasEditor(index):
    #         return False
    #     if trigger == QtWidgets.QAbstractItemView.AllEditTriggers:
    #         return True
    #     if ((trigger & self.editTriggers()) == QtWidgets.QAbstractItemView.SelectedClicked and
    #             not self.selectionModel().isSelected(index)):
    #         return False
    #     return trigger & self.editTriggers()
    #
    # def shouldForwardEvent(self, trigger, event):
    #     # type: (QtWidgets.QAbstractItemView.EditTrigger, QtCore.QEvent) -> bool
    #     if not event or (trigger & self.editTriggers()) != QtWidgets.QAbstractItemView.AnyKeyPressed:
    #         return False
    #     return event.type() in (
    #         QtCore.QEvent.KeyPress,
    #         QtCore.QEvent.MouseButtonDblClick,
    #         QtCore.QEvent.MouseButtonPress,
    #         QtCore.QEvent.MouseButtonRelease,
    #         QtCore.QEvent.MouseMove,
    #     )


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
    model.setHeaderData(0, QtCore.Qt.Horizontal, QtGui.QColor('red'), QtCore.Qt.BackgroundRole)

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
