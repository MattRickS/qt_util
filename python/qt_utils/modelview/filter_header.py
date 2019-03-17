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


class FilterLineEdit(QtWidgets.QLineEdit):
    def __init__(self, filter_field, parent=None):
        # type: (FilterField, QtWidgets.QWidget) -> None
        super(FilterLineEdit, self).__init__(parent)
        self.setPlaceholderText('Filter...')
        self.filter_field = filter_field
        self.update_style()
        self.editingFinished.connect(self.on_editing_finished)

    def mouseReleaseEvent(self, event):
        # If middle click, clear the value
        super(FilterLineEdit, self).mouseReleaseEvent(event)

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


class FilterHeader(QtWidgets.QHeaderView):
    FilterTypeRole = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None):
        super(FilterHeader, self).__init__(QtCore.Qt.Horizontal, parent)
        self.filters = []

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSectionsMovable(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        self.sectionResized.connect(self.on_section_resized)
        self.sectionMoved.connect(self.on_section_moved)

    def create_filter_field(self, logical_index):
        # Can be subclassed for custom filter parsing
        model = self.model()
        name = model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        filter_type = model.headerData(logical_index, QtCore.Qt.Horizontal, self.FilterTypeRole)
        editable = model.headerData(logical_index, QtCore.Qt.Horizontal, QtCore.Qt.EditRole)
        filter_field = FilterField(name, filter_type, editable)
        return filter_field

    def create_filter_widget(self, logical_index):
        # type: (int) -> QtWidgets.QWidget
        # Can be subclassed for custom widgets
        filter_field = self.create_filter_field(logical_index)
        # Connect editingFinished signal
        widget = FilterLineEdit(filter_field, self)
        widget.setGeometry(self.get_widget_geometry(logical_index))
        widget.show()
        self.filters.append(widget)
        return widget

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(FilterHeader, self).size()
        return QtCore.QSize(size.width(), 50)

    def showEvent(self, event):
        self.filters = []
        for i in range(self.count()):
            self.create_filter_widget(i)
        super(FilterHeader, self).showEvent(event)

    def get_widget_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        half_height = self.height() * 0.5
        return QtCore.QRect(
            self.sectionViewportPosition(logical_index) + MARGIN,
            half_height,
            self.sectionSize(logical_index) - MARGIN,
            half_height,
        )

    def on_section_resized(self, logical_index):
        for i in range(self.visualIndex(logical_index), self.count()):
            logical = self.logicalIndex(i)
            self.filters[logical].setGeometry(self.get_widget_geometry(logical))

    def on_section_moved(self, logical, old_visual_index, new_visual_index):
        for i in range(min(old_visual_index, new_visual_index), self.count()):
            logical = self.logicalIndex(i)
            self.filters[logical].setGeometry(self.get_widget_geometry(logical))

    def fix_widget_positions(self, start=0):
        for i in range(start, self.count()):
            self.filters[i].setGeometry(self.get_widget_geometry(i))


class View(QtWidgets.QTableView):
    def scrollContentsBy(self, dx, dy):
        super(View, self).scrollContentsBy(dx, dy)
        hheader = self.horizontalHeader()
        if dx != 0:
            hheader.fix_widget_positions()


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
    view = View()
    header = FilterHeader()
    view.setHorizontalHeader(header)
    view.setModel(model)
    view.show()
    # view.resizeColumnsToContents()

    app.exec_()
    sys.exit()
