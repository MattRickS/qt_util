from PySide2 import QtCore, QtGui, QtWidgets

MARGIN = 1


# Make a basic widget that paints the string/placeholder in a fake lineedit
# Have an editable widget. Ie, basically make an ItemDelegate for this.
# Actually, might be able to subclass Delegate for this...
class FilterField(object):
    def __init__(self, field_name, field_type, editable=True):
        # type: (str, type, bool) -> None
        self.name = field_name
        self.type = field_type
        self.editable = editable

        self._auto_apply = False
        self._saved = ''
        self._method = None
        self._string = ''
        self._valid = True
        self._value = None

    def __repr__(self):
        return 'FilterField({!r}, {}, {})'.format(self.name, self.type, self.editable)

    @property
    def auto_apply(self):
        # type: () -> bool
        return self._auto_apply

    @property
    def method(self):
        # type: () -> str
        """ The current method in the filter """
        return self._method

    @property
    def string(self):
        # type: () -> str
        """ The display string being stored in the FilterField """
        return self._string

    @property
    def valid(self):
        # type: () -> bool
        """ Whether or not the display string is a valid filter """
        return self._valid

    @property
    def value(self):
        # type: () -> object
        """ The current value for the filter method """
        return self._value

    def clear(self, force=False):
        # type: (bool) -> bool
        """ Clears the current values if editable or forced """
        if not force and not self.editable:
            return False
        self._method = None
        self._string = ''
        self._valid = True
        self._value = None
        return True

    def is_modified(self):
        # type: () -> bool
        """ Whether or not the filter is considered applied """
        return self._saved != self._string

    def restore(self):
        """ Restores the internal data to the last applied state """
        if not self._saved:
            self.clear(force=True)
        elif self.is_modified():
            self.set(self._saved)

    def save(self):
        # type: () -> bool
        """ Saves a copy of the current state of the filters if they are valid """
        if not self._valid:
            return False
        self._saved = self._string
        return True

    def set(self, string):
        # type: (str) -> bool
        """ Sets a string value on the FilterField, updating the internal filters """
        if not self.editable:
            return False

        self._string = string
        try:
            self._method, self._value = '', ''  # filter_strings.parse_string(string, self.name, self.type)
            self._valid = True
            if self._auto_apply:
                self.save()
        except ValueError:
            self._valid = False

        return self._valid

    def set_auto_apply(self, auto_apply):
        # type: (bool) -> None
        self._auto_apply = auto_apply
        if self.is_modified():
            self.save()


class HeaderWidget(QtWidgets.QWidget):
    editingFinished = QtCore.Signal()
    headerDataChanged = QtCore.Signal(int, object)  # Role, value

    def on_header_data_changed(self, role, value):
        pass


class FilterLineEdit(QtWidgets.QLineEdit):
    headerDataChanged = QtCore.Signal(int, object)  # Role, value

    def __init__(self, filter_field, parent=None):
        # type: (FilterField, QtWidgets.QWidget) -> None
        super(FilterLineEdit, self).__init__(parent)
        self.setPlaceholderText('Filter...')
        self.filter_field = filter_field
        self.update_style()
        self.editingFinished.connect(self.on_editing_finished)

    def update_style(self):
        if not self.filter_field.editable:
            colour = 'black'
        elif not self.filter_field.valid:
            colour = 'red'
        elif self.filter_field.is_modified():
            colour = 'cyan'
        elif self.filter_field.string:
            colour = 'darkorange'
        else:
            colour = 'orange'

        self.setStyleSheet(' QWidget { background: %s; } ' % colour)

    def on_editing_finished(self):
        self.filter_field.set(self.text())
        self.update_style()


class FilterComboBoolean(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(FilterComboBoolean, self).__init__(parent)
        self.addItems(['No Filter', 'True', 'False'])


class WidgetHeaderView(QtWidgets.QHeaderView):
    HeaderDataRole = QtCore.Qt.UserRole + 1000
    HeaderDataTypeRole = QtCore.Qt.UserRole + 1001

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

    def set_default_widget(self, widget_cls):
        self.set_widget_type(None, widget_cls)

    def create_header_widget(self, logical_index):
        # type: (int) -> QtWidgets.QWidget
        # Can be subclassed for custom widgets
        model = self.model()
        name = model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        data_type = model.headerData(logical_index, QtCore.Qt.Horizontal, self.HeaderDataRole)
        editable = model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.EditRole)
        filter_field = FilterField(name, data_type, editable)
        widget = FilterLineEdit(filter_field, self)
        # Can ensure the widget stays up to date with the source model
        # self.headerDataChanged.connect()
        return widget

    def get_header_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        half_height = self.height() * 0.5
        return QtCore.QRect(
            self.sectionViewportPosition(logical_index) + MARGIN,
            0,
            self.sectionSize(logical_index) - MARGIN,
            half_height,
        )

    def get_widget_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        half_height = self.height() * 0.5
        return QtCore.QRect(
            self.sectionViewportPosition(logical_index) + MARGIN,
            half_height,
            self.sectionSize(logical_index) - MARGIN,
            half_height,
        )

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(WidgetHeaderView, self).size()
        return QtCore.QSize(size.width(), 50)

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        # Render the filter widget in the header widget rect
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
        if 0 <= index < self.count():
            rect = self.get_widget_geometry(index)
            if rect.contains(event.pos()):
                widget = self._widgets[index]
                widget.setGeometry(rect)
                # TODO: This won't work for everything, will require a base class
                widget.editingFinished.connect(widget.close)
                widget.show()
                widget.setFocus(QtCore.Qt.MouseFocusReason)
                # Prevent interaction with the widget region from
                # triggering a section click
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
    header = WidgetHeaderView()
    view.setHorizontalHeader(header)
    view.setSortingEnabled(True)
    view.setModel(model)
    view.show()
    # view.resizeColumnsToContents()

    app.exec_()
    sys.exit()
