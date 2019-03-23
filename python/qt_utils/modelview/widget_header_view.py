from PySide2 import QtCore, QtGui, QtWidgets

MARGIN = 1


class WidgetHeaderView(QtWidgets.QHeaderView):
    HeaderDataRole = QtCore.Qt.UserRole + 1000
    HeaderDataTypeRole = HeaderDataRole + 1
    HeaderEditRole = HeaderDataRole + 2

    def __init__(self, parent=None):
        super(WidgetHeaderView, self).__init__(QtCore.Qt.Horizontal, parent)
        self._widgets = []
        self._widget_type_mapping = {}

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

    def set_widget_type(self, data_type, widget_cls):
        # Convenience method for setting the widget type to use for particular
        # data types. Data types are anything returned by the model for the
        # HeaderDataTypeRole
        self._widget_type_mapping[data_type] = widget_cls
        for i, w in enumerate(self._widgets):
            if self.model().headerData(i, self.orientation(), self.HeaderDataTypeRole) == data_type:
                self._widgets[i] = self.create_header_widget(i)
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()

    def set_default_widget(self, widget_cls):
        self.set_widget_type(None, widget_cls)

    def has_widget(self, logical_index):
        try:
            return self._widgets[logical_index] is not None
        except IndexError:
            return False

    def create_header_widget(self, logical_index):
        # type: (int) -> QtWidgets.QWidget
        # Can be subclassed for custom widgets
        model = self.model()
        data_type = model.headerData(logical_index, QtCore.Qt.Horizontal, self.HeaderDataTypeRole)
        cls = self._widget_type_mapping.get(data_type, self._widget_type_mapping.get(None))
        if cls is None:
            return
        widget = cls(self, logical_index, self.orientation(), self)
        return widget
        # model = self.model()
        # name = model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        # value = model.headerData(logical_index, QtCore.Qt.Horizontal, self.HeaderDataRole)
        # data_type = model.headerData(logical_index, QtCore.Qt.Horizontal, self.HeaderDataTypeRole)
        # editable = model.headerData(logical_index, QtCore.Qt.Horizontal, self.HeaderEditRole)
        # filter_field = FilterField(name, data_type, editable)
        # widget = FilterLineEdit(filter_field, self)
        # # Can ensure the widget stays up to date with the source model
        # # self.headerDataChanged.connect()
        # return widget

    def get_header_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        if self.has_widget(logical_index):
            half_height = self.height() * 0.5
            return QtCore.QRect(
                self.sectionViewportPosition(logical_index) + MARGIN,
                0,
                self.sectionSize(logical_index) - MARGIN,
                half_height,
            )
        else:
            return QtCore.QRect(
                self.sectionViewportPosition(logical_index) + MARGIN,
                0,
                self.sectionSize(logical_index) - MARGIN,
                self.height(),
            )

    def get_widget_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        if self.has_widget(logical_index):
            half_height = self.height() * 0.5
            return QtCore.QRect(
                self.sectionViewportPosition(logical_index) + MARGIN,
                half_height,
                self.sectionSize(logical_index) - MARGIN,
                half_height,
            )
        else:
            return self.get_header_geometry(logical_index)

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(WidgetHeaderView, self).size()
        return QtCore.QSize(size.width(), 50)

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        # Render the filter widget in the header widget rect
        if self.has_widget(logical_index):
            painter.save()
            widget_geo = self.get_widget_geometry(logical_index)
            painter.translate(widget_geo.topLeft())
            widget = self._widgets[logical_index]
            widget.resize(widget_geo.size())
            widget.render(painter, QtCore.QPoint())
            painter.restore()

        # Render the original header section in the remaining area
        header_geo = self.get_header_geometry(logical_index)
        super(WidgetHeaderView, self).paintSection(painter, header_geo, logical_index)

    def mouseReleaseEvent(self, event):
        clickable = self.sectionsClickable()
        # Check if the release happens in the region of a widget and if so,
        # display the widget
        index = self.logicalIndexAt(event.pos())
        if self.has_widget(index):
            rect = self.get_widget_geometry(index)
            if rect.contains(event.pos()):
                widget = self._widgets[index]
                widget.setGeometry(rect)
                # Would it be possible to just show the widget whenever the
                # mouse enters a widget region and hide it when it leaves? This
                # would prevent keyboard entry being visible (but still occuring)
                # if the mouse moved off the region. Hard to handle focus
                # TODO: This won't work for everything, will require a base class
                widget.editingFinished.connect(widget.close)
                widget.show()
                widget.setFocus(QtCore.Qt.MouseFocusReason)
                # Prevent interaction with the widget region from triggering a
                # section click, otherwise it will be sorted (if sorting is
                # enabled). Note: setSortIndicator is not virtual so overriding
                # it explicitly is not possible
                # TODO: This prevents the viewport from moving to ensure the
                # column width is fully visible
                self.setSectionsClickable(False)
        super(WidgetHeaderView, self).mouseReleaseEvent(event)
        if self.sectionsClickable() != clickable:
            self.setSectionsClickable(clickable)

    def resizeEvent(self, event):
        super(WidgetHeaderView, self).resizeEvent(event)
        # Because we're manually setting the widget geometry to make it visible,
        # it will not respond correctly to the viewport being modified. Ensure
        # the widget is hidden and loses any focus.
        for widget in self._widgets:
            if widget is None:
                continue
            if widget.hasFocus():
                widget.clearFocus()
            if widget.isVisible():
                widget.close()

    def showEvent(self, event):
        # Create a widget for each column
        self._widgets = [self.create_header_widget(i) for i in range(self.count())]
        super(WidgetHeaderView, self).showEvent(event)


if __name__ == '__main__':
    import sys

    def update_style(widget, view, section, orientation):
        return
        editable = view.model().headerData(section, orientation, view.HeaderEditRole)
        value = view.model().headerData(section, orientation, view.HeaderDataRole)
        if editable is False:
            colour = 'black'
        # elif not filter_field.valid:
        #     colour = 'red'
        # elif filter_field.is_modified():
        #     colour = 'cyan'
        elif value:
            colour = 'darkorange'
        else:
            colour = 'orange'

        widget.setStyleSheet(' QWidget { background: %s; } ' % colour)


    class FilterLineEdit(QtWidgets.QLineEdit):
        def __init__(self, view, section, orientation, parent=None):
            # type: (WidgetHeaderView, int, QtCore.Qt.Orientation, QtWidgets.QWidget) -> None
            super(FilterLineEdit, self).__init__(parent)
            self.view = view
            self.orientation = orientation
            self.section = section

            self.editingFinished.connect(self.on_editing_finished)

            self.setPlaceholderText('Filter...')
            update_style(self, self.view, self.section, self.orientation)

        def on_editing_finished(self):
            self.view.model().setHeaderData(
                self.section,
                self.orientation,
                self.text(),
                self.view.HeaderDataRole
            )
            update_style(self, self.view, self.section, self.orientation)


    class FilterComboBoolean(QtWidgets.QComboBox):
        editingFinished = QtCore.Signal()

        def __init__(self, view, section, orientation, parent=None):
            super(FilterComboBoolean, self).__init__(parent)
            self.view = view
            self.orientation = orientation
            self.section = section
            self.addItems(['Filter...', 'True', 'False'])
            update_style(self, self.view, self.section, self.orientation)

            self.currentIndexChanged.connect(self.editingFinished)

        def showEvent(self, event):
            super(FilterComboBoolean, self).showEvent(event)
            self.showPopup()

    app = QtWidgets.QApplication(sys.argv)

    model = QtGui.QStandardItemModel()
    model.setHorizontalHeaderLabels([
        'name',
        'age',
        'gender',
        'surname',
        'is_artist',
    ])
    model.setHeaderData(4, QtCore.Qt.Horizontal, bool, WidgetHeaderView.HeaderDataTypeRole)
    model.insertRow(0, [
        QtGui.QStandardItem('ray'),
        QtGui.QStandardItem('30'),
        QtGui.QStandardItem('male'),
        QtGui.QStandardItem('barrett'),
        QtGui.QStandardItem(''),
    ])
    model.insertRow(1, [
        QtGui.QStandardItem('emma'),
        QtGui.QStandardItem('30'),
        QtGui.QStandardItem('female'),
        QtGui.QStandardItem('dunlop'),
        QtGui.QStandardItem(''),
    ])
    view = QtWidgets.QTableView()
    header = WidgetHeaderView()
    header.set_default_widget(FilterLineEdit)
    header.set_widget_type(bool, FilterComboBoolean)
    view.setHorizontalHeader(header)
    view.setSortingEnabled(True)
    view.setModel(model)
    view.show()

    app.exec_()
    sys.exit()
