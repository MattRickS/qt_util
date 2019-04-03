from typing import Type

from PySide2 import QtCore, QtGui, QtWidgets


class Separator(QtWidgets.QPushButton):
    def __init__(self):
        super(Separator, self).__init__('>')
        self.setFixedWidth(20)


class BreadCrumb(QtWidgets.QPushButton):
    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.text())


class BreadCrumbWidget(QtWidgets.QWidget):
    breadcrumbClicked = QtCore.Signal(object, int)  # index, BreadCrumb
    separatorClicked = QtCore.Signal(object, int)  # index, Separator

    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(BreadCrumbWidget, self).__init__(parent)
        self._hidden_separators = False
        self._separator_widget = Separator
        self._breadcrumb_widget = BreadCrumb
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(self._layout)

    @property
    def breadcrumb_widget(self):
        # type: () -> Type[BreadCrumb]
        """ The BreadCrumb class being used """
        return self._breadcrumb_widget

    @property
    def separators_hidden(self):
        # type: () -> bool
        """ Whether or not separators are visible in the path """
        return self._hidden_separators

    @property
    def separator_widget(self):
        # type: () -> Type[Separator]
        """ The Separator class being used """
        return self._separator_widget

    def add_breadcrumb(self, name):
        # type: (str) -> BreadCrumb
        """ Adds a breadcrumb to the path """
        count = self._layout.count()
        if count:
            self._layout.addWidget(self.create_separator(count // 2))

        breadcrumb = self.create_breadcrumb(name, count // 2)
        self._layout.addWidget(breadcrumb)
        return breadcrumb

    def back(self):
        """ Removes the last breadcrumb and separator in the path """
        count = self._layout.count()
        if not count:
            raise IndexError('Nothing to remove')
        self._remove_index(count - 1)
        if self._layout.count():
            self._remove_index(count - 2)

    def clear(self):
        """ Clears the path """
        for i in reversed(range(self._layout.count())):
            self._remove_index(i)

    def create_breadcrumb(self, name, index):
        # type: (str, int) -> BreadCrumb
        """ Creates and connects the BreadCrumb """
        breadcrumb = self._breadcrumb_widget(name)
        breadcrumb.clicked.connect(self.on_breadcrumb_clicked)
        return breadcrumb

    def create_separator(self, index):
        # type: (int) -> Separator
        """ Creates and connects the separator """
        separator = self._separator_widget()
        separator.clicked.connect(self.on_separator_clicked)
        separator.setHidden(self._hidden_separators)
        return separator

    def get_breadcrumb(self, index):
        # type: (int) -> BreadCrumb|None
        """ Gets the BreadCrumb widget at the given index """
        item = self._layout.itemAt(index * 2)
        if item is None:
            return
        return item.widget()

    def get_separator(self, index):
        # type: (int) -> Separator|None
        """ Gets the Separator widget at the given index """
        item = self._layout.itemAt(index * 2 + 1)
        if item is None:
            return
        return item.widget()

    def get_path(self, end=-1):
        # type: (int) -> list[str]
        """ Returns the list of current breadcrumb names """
        total = self._layout.count()
        end = total if end == -1 else max(total, (end + 1) * 2)
        return [self._layout.itemAt(i).widget().text() for i in range(0, end, 2)]

    def set_alignment(self, alignment):
        # type: (QtCore.Qt.Alignment) -> None
        """ Sets the alignment for the widgets in the path """
        self._layout.setAlignment(alignment)

    def set_breadcrumb_widget(self, cls):
        # type: (Type[BreadCrumb]) -> None
        """ Sets the widget class to use for the breadcrumbs """
        self._breadcrumb_widget = cls
        for i in range(0, self._layout.count(), 2):
            name = self._layout.itemAt(i).widget().text()
            self._remove_index(i)
            self._layout.insertWidget(i, self.create_breadcrumb(name, i // 2))

    def set_path(self, path):
        # type: (list[str]) -> None
        """ Sets the list of current breadcrumb names """
        self.clear()
        for name in path:
            self.add_breadcrumb(name)

    def set_separator_widget(self, cls):
        # type: (Type[Separator]) -> None
        """ Sets the widget class to use for the separators """
        self._separator_widget = cls
        for i in range(1, self._layout.count(), 2):
            self._remove_index(i)
            self._layout.insertWidget(i, self.create_separator((i - 1) // 2))

    def set_separators_hidden(self, hidden):
        # type: (bool) -> None
        """ Sets whether or not the separators are visible in the path """
        self._hidden_separators = hidden
        for i in range(1, self._layout.count(), 2):
            separator = self._layout.itemAt(i).widget()
            separator.setHidden(self._hidden_separators)

    def on_breadcrumb_clicked(self):
        widget = self.sender()
        index = self._layout.indexOf(widget)
        self.breadcrumbClicked.emit(widget, index // 2)

    def on_separator_clicked(self):
        widget = self.sender()
        index = self._layout.indexOf(widget)
        self.separatorClicked.emit(widget, (index - 1) // 2)

    def _remove_index(self, index):
        # type: (int) -> None
        widget = self._layout.takeAt(index).widget()
        widget.setParent(None)
        widget.destroy()


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)


    class Widget(QtWidgets.QWidget):
        def __init__(self, value=None, parent=None):
            # type: (list[str], QtWidgets.QWidget) -> None
            super(Widget, self).__init__(parent)

            # ----- Widgets -----

            class BreadcrumbRed(BreadCrumb):
                def __init__(self, name):
                    super(BreadcrumbRed, self).__init__(name)
                    self.setFixedWidth(50)
                    self.setStyleSheet('BreadCrumb {background: red;}')

            class SeparatorRed(Separator):
                def __init__(self):
                    super(SeparatorRed, self).__init__()
                    self.setStyleSheet('Separator {background: red;}')

            self.breadcrumb = BreadCrumbWidget()
            self.back_btn = QtWidgets.QPushButton('back')
            self.clear_btn = QtWidgets.QPushButton('clear')
            self.reset_btn = QtWidgets.QPushButton('reset')
            self.add_btn = QtWidgets.QPushButton('add')
            self.toggle_btn = QtWidgets.QPushButton('toggle')
            self.print_btn = QtWidgets.QPushButton('print')
            self.crumb_btn = QtWidgets.QPushButton('change breadcrumb')
            self.sep_btn = QtWidgets.QPushButton('change separator')

            # ----- Layout -----

            main_layout = QtWidgets.QVBoxLayout()
            main_layout.addWidget(self.breadcrumb)
            main_layout.addWidget(self.back_btn)
            main_layout.addWidget(self.clear_btn)
            main_layout.addWidget(self.reset_btn)
            main_layout.addWidget(self.add_btn)
            main_layout.addWidget(self.toggle_btn)
            main_layout.addWidget(self.print_btn)
            main_layout.addWidget(self.crumb_btn)
            main_layout.addWidget(self.sep_btn)
            self.setLayout(main_layout)

            # ----- Connections -----

            self.add_btn.clicked.connect(lambda : self.breadcrumb.add_breadcrumb('added'))
            self.back_btn.clicked.connect(self.breadcrumb.back)
            self.clear_btn.clicked.connect(self.breadcrumb.clear)
            self.toggle_btn.clicked.connect(
                lambda: self.breadcrumb.set_separators_hidden(not self.breadcrumb.separators_hidden)
            )
            self.reset_btn.clicked.connect(lambda: self.breadcrumb.set_path(value or []))
            self.print_btn.clicked.connect(lambda: print(self.breadcrumb.get_path()))
            self.crumb_btn.clicked.connect(lambda: self.breadcrumb.set_breadcrumb_widget(BreadcrumbRed))
            self.sep_btn.clicked.connect(lambda: self.breadcrumb.set_separator_widget(SeparatorRed))
            self.breadcrumb.breadcrumbClicked.connect(self.debug)
            self.breadcrumb.separatorClicked.connect(self.debug)

            # ----- Initialise -----

            if value is not None:
                self.breadcrumb.set_path(value)

        def debug(self, *args):
            print('Slot:', args)

    w = Widget(['one', 'two', 'three'])
    w.show()

    app.exec_()
    sys.exit()
