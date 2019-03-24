from typing import Type

from PySide2 import QtCore, QtGui, QtWidgets

MARGIN = 1


class HeaderWidget(QtWidgets.QWidget):
    editingFinished = QtCore.Signal()

    HeaderDataRole = QtCore.Qt.UserRole + 1000
    HeaderDataTypeRole = HeaderDataRole + 1
    HeaderEditRole = HeaderDataRole + 2

    def __init__(self, view, section, orientation, parent=None):
        # type: (WidgetHeaderView, int, QtCore.Qt.Orientation, QtWidgets.QWidget) -> None
        super(HeaderWidget, self).__init__(parent)
        self.view = view
        self.orientation = orientation
        self.section = section

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def focusInEvent(self, event):
        super(HeaderWidget, self).focusInEvent(event)
        widget = self.widget()
        if widget is not None:
            widget.setFocus(event.reason())

    def data(self, role):
        return self.view.model().headerData(
            self.section,
            self.orientation,
            role,
        )

    def set_data(self, role, value):
        self.view.model().setHeaderData(
            self.section,
            self.orientation,
            value,
            role,
        )

    def widget(self):
        item = self.layout().itemAt(0)
        return item.widget() if item else None

    def set_widget(self, widget):
        while self.layout().count():
            self.layout().takeAt(0)
        if widget:
            self.layout().addWidget(widget)

    def update_widget(self):
        editable = self.view.model().headerData(
            self.section,
            self.orientation,
            HeaderWidget.HeaderEditRole
        )
        # Default will be None, but for the majority of cases, widgets will need
        # to be enabled by default so None should not disable the widget
        self.setEnabled(editable is not False)


class HeaderLineEdit(HeaderWidget):
    def __init__(self, view, section, orientation, parent):
        super(HeaderLineEdit, self).__init__(view, section, orientation, parent)
        edit = QtWidgets.QLineEdit()
        edit.editingFinished.connect(self.on_widget_editing_finished)
        self.set_widget(edit)

    def on_widget_editing_finished(self):
        self.set_data(HeaderWidget.HeaderDataRole, self.widget().text())
        self.editingFinished.emit()

    def update_widget(self):
        super(HeaderLineEdit, self).update_widget()
        value = self.data(HeaderWidget.HeaderDataRole)
        self.widget().setText(str(value) if value else '')


class WidgetHeaderView(QtWidgets.QHeaderView):
    def __init__(self, orientation, parent=None):
        super(WidgetHeaderView, self).__init__(orientation, parent)
        self._widgets = []
        self._widget_type_mapping = {
            None: HeaderLineEdit
        }
        self._data_types_only = False

        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

    def create_header_widget(self, logical_index):
        # type: (int) -> QtWidgets.QWidget|None
        """ Creates the widget for the index """
        # Can be subclassed for custom widgets
        model = self.model()
        data_type = model.headerData(logical_index,
                                     QtCore.Qt.Horizontal,
                                     HeaderWidget.HeaderDataTypeRole)
        if data_type is None and self._data_types_only:
            return
        cls = self._widget_type_mapping.get(data_type, self._widget_type_mapping.get(None))
        widget = None if cls is None else cls(self, logical_index, self.orientation(), self)
        return widget

    def get_header_geometry(self, logical_index):
        # type: (int) -> QtCore.QRect
        """ The geometry rect within the header for the standard header """
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
        """ The geometry rect within the header for the widget """
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

    def has_widget(self, logical_index):
        # type: (int) -> bool
        """ Whether or not a widget exists for the given index """
        try:
            return self._widgets[logical_index] is not None
        except IndexError:
            return False

    def remove_header_widget(self, index):
        # type: (int) -> None
        """ Removes the widget from the view """
        try:
            widget = self._widgets[index]
        except IndexError:
            return
        self._widgets[index] = None
        if widget.isVisible():
            widget.hide()
        widget.setParent(None)
        widget.deleteLater()

    def set_datatypes_only(self, datatypes_only):
        # type: (bool) -> None
        """ Whether or not to generate widgets for None values. Modifies existing widgets. """
        self._data_types_only = datatypes_only
        for i, w in enumerate(self._widgets):
            if self.model().headerData(i,
                                       self.orientation(),
                                       HeaderWidget.HeaderDataTypeRole) is None:
                if w and datatypes_only:
                    self.remove_header_widget(i)
                elif w is None and not datatypes_only:
                    self._widgets[i] = self.create_header_widget(i)

    def set_default_widget(self, widget_cls):
        # type: (Type[QtWidgets.QWidget]) -> None
        """
        Sets the widget class to initialise for unknown datatypes using the
        standard create_header_widget(). Modifies existing widgets.
        """
        self.set_widget_type(None, widget_cls)

    def set_widget_type(self, data_type, widget_cls):
        # type: (object, Type[QtWidgets.QWidget]) -> None
        """
        Sets the widget class to use for a data type as returned by the
        HeaderDataTypeRole. Modifies existing widgets.
        """
        # Convenience method for setting the widget type to use for particular
        # data types. Data types are anything returned by the model for the
        # HeaderDataTypeRole
        self._widget_type_mapping[data_type] = widget_cls
        for i, w in enumerate(self._widgets):
            if self.model().headerData(i,
                                       self.orientation(),
                                       HeaderWidget.HeaderDataTypeRole) == data_type:
                self._widgets[i] = self.create_header_widget(i)
                if w is not None:
                    self.remove_header_widget(i)

    # ======================================================================== #
    #  Subclassed
    # ======================================================================== #

    def headerDataChanged(self, orientation, first, last):
        # type: (QtCore.Qt.Orientation, int, int) -> None
        super(WidgetHeaderView, self).headerDataChanged(orientation, first, last)
        if orientation != self.orientation():
            return
        for i in range(first, min(len(self._widgets), last + 1)):
            widget = self._widgets[i]
            if widget is None:
                continue
            widget.update_widget()

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

    def setModel(self, model):
        curr_model = self.model()
        if curr_model:
            curr_model.headerDataChanged.disconnect(self.headerDataChanged)
        if model:
            model.headerDataChanged.connect(self.headerDataChanged)
        super(WidgetHeaderView, self).setModel(model)

    def sizeHint(self):
        # type: () -> QtCore.QSize
        size = super(WidgetHeaderView, self).size()
        return QtCore.QSize(size.width(), 50)

    # ======================================================================== #
    #  Events
    # ======================================================================== #

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
                widget.editingFinished.connect(widget.close)
                widget.show()
                widget.setFocus(QtCore.Qt.MouseFocusReason)
                # Prevent interaction with the widget region from triggering a
                # section click, otherwise it will be sorted (if sorting is
                # enabled). Note: setSortIndicator is not virtual so overriding
                # it explicitly is not possible
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
        # Create a widget for each column/row
        self._widgets = [self.create_header_widget(i) for i in range(self.count())]
        super(WidgetHeaderView, self).showEvent(event)


if __name__ == '__main__':
    import sys


    class Model(QtCore.QAbstractTableModel):
        HeaderBackgroundRole = QtCore.Qt.UserRole + 1

        def __init__(self, parent=None):
            # type: (QtWidgets.QWidget) -> None
            super(Model, self).__init__(parent)
            self._entities = [
                ['ray', 30, 'male', False],
                ['emma', 30, 'female', True],
            ]
            self.filters = {}
            self.columns = [
                {'name': 'name', 'filter': None, 'type': str, 'editable': True, 'valid': True, 'edited': False},
                {'name': 'age', 'filter': None, 'type': int, 'editable': True, 'valid': True, 'edited': False},
                {'name': 'gender', 'filter': None, 'type': str, 'editable': False, 'valid': True, 'edited': False},
                {'name': 'is_artist', 'filter': None, 'type': bool, 'editable': True, 'valid': True, 'edited': False},
            ]

        def columnCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self.columns)

        def data(self, index, role=QtCore.Qt.DisplayRole):
            # type: (QtCore.QModelIndex, int) -> object
            if not index.isValid():
                return
            if role == QtCore.Qt.DisplayRole:
                return self._entities[index.row()][index.column()]

        def flags(self, index):
            # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
            # type: (int, QtCore.Qt.Orientation, int) -> str
            if orientation == QtCore.Qt.Horizontal:
                data = self.columns[section]
                if role == QtCore.Qt.DisplayRole:
                    return data['name']
                elif role == HeaderWidget.HeaderDataRole:
                    return data['filter']
                elif role == HeaderWidget.HeaderDataTypeRole:
                    return data['type']
                elif role == HeaderWidget.HeaderEditRole:
                    return data['editable']
                elif role == Model.HeaderBackgroundRole:
                    if data['editable'] is False:
                        colour = 'grey'
                    elif not data['valid']:
                        colour = 'red'
                    elif data['edited']:
                        colour = 'cyan'
                    elif data['filter']:
                        colour = 'darkorange'
                    else:
                        colour = 'orange'
                    return colour

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self._entities)

        def setHeaderData(self, section, orientation, value, role=QtCore.Qt.EditRole):
            if orientation == QtCore.Qt.Horizontal:
                mapping = {
                    QtCore.Qt.DisplayRole: 'name',
                    HeaderWidget.HeaderDataTypeRole: 'type',
                    HeaderWidget.HeaderDataRole: 'filter',
                    HeaderWidget.HeaderEditRole: 'editable',
                }
                key = mapping[role]
                data = self.columns[section]
                if key in data:
                    data[key] = value
                    if role == HeaderWidget.HeaderDataRole:
                        if value == '':
                            value = None
                        existing = self.filters.get(data['name'])
                        data['edited'] = value != existing
                        if value is None:
                            data[key] = None
                            data['valid'] = True
                        else:
                            try:
                                data[key] = data['type'](value)
                                data['valid'] = True
                            except ValueError:
                                data['valid'] = False
                    self.headerDataChanged.emit(orientation, section, section)
                    return True
            return False

        def setData(self, index, value, role=QtCore.Qt.EditRole):
            # type: (QtCore.QModelIndex, object, int) -> bool
            if not index.isValid():
                return False


    def update_style(header_widget):
        # type: (HeaderWidget) -> None
        editable = header_widget.data(HeaderWidget.HeaderEditRole)
        header_widget.setEnabled(editable)
        colour = header_widget.data(Model.HeaderBackgroundRole)
        if colour is not None:
            header_widget.widget().setStyleSheet(
                ' QWidget { background: %s; } ' % colour
            )


    class FilterLineEdit(HeaderLineEdit):
        def __init__(self, view, section, orientation, parent=None):
            # type: (WidgetHeaderView, int, QtCore.Qt.Orientation, QtWidgets.QWidget) -> None
            super(FilterLineEdit, self).__init__(view, section, orientation, parent)
            self.widget().setPlaceholderText('Filter...')
            self.update_widget()

        def update_widget(self):
            super(FilterLineEdit, self).update_widget()
            update_style(self)


    class FilterComboBoolean(HeaderWidget):
        NO_FILTER = 'Filter...'

        editingFinished = QtCore.Signal()

        def __init__(self, view, section, orientation, parent=None):
            super(FilterComboBoolean, self).__init__(view, section, orientation, parent)
            combo = QtWidgets.QComboBox()
            combo.addItems([self.NO_FILTER, 'True', 'False'])
            combo.currentTextChanged.connect(self.on_widget_text_changed)
            self.set_widget(combo)
            self.update_widget()

        def on_widget_text_changed(self, text):
            self.set_data(HeaderWidget.HeaderDataRole, bool(text) if text != self.NO_FILTER else None)
            self.editingFinished.emit()

        def update_widget(self):
            super(FilterComboBoolean, self).update_widget()
            value = self.data(HeaderWidget.HeaderDataRole)
            self.widget().setCurrentText(str(value) if value else self.NO_FILTER)
            update_style(self)

        def showEvent(self, event):
            super(FilterComboBoolean, self).showEvent(event)
            self.widget().showPopup()

    app = QtWidgets.QApplication(sys.argv)

    model = Model()
    view = QtWidgets.QTableView()
    header = WidgetHeaderView(QtCore.Qt.Horizontal)
    header.set_default_widget(FilterLineEdit)
    header.set_widget_type(bool, FilterComboBoolean)
    header.setStretchLastSection(True)
    view.setHorizontalHeader(header)
    view.setSortingEnabled(True)
    view.setModel(model)
    view.show()

    app.exec_()
    for d in model.columns:
        print(d)
    sys.exit()
