from PySide2 import QtCore, QtGui, QtWidgets


class SpoilerButton(QtWidgets.QWidget):
    toggled = QtCore.Signal(bool)

    def __init__(self, text=''):
        super(SpoilerButton, self).__init__()

        self._button = QtWidgets.QToolButton()
        self._button.setStyleSheet("QToolButton { border: none; }")
        self._button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._button.setArrowType(QtCore.Qt.RightArrow)
        self._button.setText(str(text))
        self._button.setCheckable(True)
        self._button.setChecked(False)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        spoiler_layout = QtWidgets.QHBoxLayout()
        spoiler_layout.addWidget(self._button)
        spoiler_layout.addWidget(line)
        self.setLayout(spoiler_layout)

        self._button.toggled.connect(self.on_button_toggled)

    def on_button_toggled(self):
        checked = self._button.isChecked()
        arrow_type = QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        self._button.setArrowType(arrow_type)
        self.toggled.emit(checked)


class SpoilerWidget(QtWidgets.QWidget):
    def __init__(self, text='', widget=None):
        super(SpoilerWidget, self).__init__()

        self._button = QtWidgets.QToolButton()
        self._button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._button.setArrowType(QtCore.Qt.RightArrow)
        self._button.setText(str(text))
        self._button.setCheckable(True)
        self._button.setChecked(False)

        self._widget = QtWidgets.QScrollArea()
        self._widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self._collapser = Collapser(widget=self._widget)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        spoiler_layout = QtWidgets.QHBoxLayout()
        spoiler_layout.addWidget(self._button)
        spoiler_layout.addWidget(line)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(spoiler_layout)
        main_layout.addWidget(self._widget)
        self.setLayout(main_layout)

        if widget is not None:
            self.set_widget(widget)

    def set_layout(self, layout):
        self._widget.setLayout(layout)

    def on_button_toggled(self):
        arrow_type = QtCore.Qt.DownArrow if self._button.isChecked() else QtCore.Qt.RightArrow
        self._button.setArrowType(arrow_type)


class Spoiler(QtWidgets.QWidget):
    def __init__(self, parent=None, title='', animationDuration=300):
        """
        References:
            # Adapted from c++ version
            http://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt
        """
        super(Spoiler, self).__init__(parent=parent)

        self.animationDuration = animationDuration
        self.toggleAnimation = QtCore.QParallelAnimationGroup()
        self.contentArea = QtWidgets.QScrollArea()
        self.headerLine = QtWidgets.QFrame()
        self.toggleButton = QtWidgets.QToolButton()
        self.mainLayout = QtWidgets.QGridLayout()

        toggleButton = self.toggleButton
        toggleButton.setStyleSheet("QToolButton { border: none; }")
        toggleButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toggleButton.setArrowType(QtCore.Qt.RightArrow)
        toggleButton.setText(str(title))
        toggleButton.setCheckable(True)
        toggleButton.setChecked(False)

        headerLine = self.headerLine
        headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        headerLine.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        self.contentArea.setStyleSheet("QScrollArea { background-color: white; border: none; }")
        self.contentArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # start out collapsed
        self.contentArea.setMaximumHeight(0)
        self.contentArea.setMinimumHeight(0)
        # let the entire widget grow and shrink with its content
        toggleAnimation = self.toggleAnimation
        toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, "minimumHeight"))
        toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, "maximumHeight"))
        toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self.contentArea, "maximumHeight"))
        # don't waste space
        mainLayout = self.mainLayout
        mainLayout.setVerticalSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        row = 0
        mainLayout.addWidget(self.toggleButton, row, 0, 1, 1, QtCore.Qt.AlignLeft)
        mainLayout.addWidget(self.headerLine, row, 2, 1, 1)
        row += 1
        mainLayout.addWidget(self.contentArea, row, 0, 1, 3)
        self.setLayout(self.mainLayout)

        def start_animation():
            arrow_type = QtCore.Qt.DownArrow if toggleButton.isChecked() else QtCore.Qt.RightArrow
            direction = QtCore.QAbstractAnimation.Forward if toggleButton.isChecked() else QtCore.QAbstractAnimation.Backward
            toggleButton.setArrowType(arrow_type)
            self.toggleAnimation.setDirection(direction)
            self.toggleAnimation.start()

        self.toggleButton.clicked.connect(start_animation)

    def setContentLayout(self, contentLayout):
        # Not sure if this is equivalent to self.contentArea.destroy()
        self.contentArea.destroy()
        self.contentArea.setLayout(contentLayout)
        collapsedHeight = self.sizeHint().height() - self.contentArea.maximumHeight()
        contentHeight = contentLayout.sizeHint().height()
        for i in range(self.toggleAnimation.animationCount() - 1):
            spoilerAnimation = self.toggleAnimation.animationAt(i)
            spoilerAnimation.setDuration(self.animationDuration)
            spoilerAnimation.setStartValue(collapsedHeight)
            spoilerAnimation.setEndValue(collapsedHeight + contentHeight)
        contentAnimation = self.toggleAnimation.animationAt(
            self.toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self.animationDuration)
        contentAnimation.setStartValue(0)
        contentAnimation.setEndValue(contentHeight)


"""

[Optional] Window whose size increases/decreases with the expand/collapse
* Best way to achieve this without forcing a particular window class is to use a 
  signal on the container that emits when it's changing size so that another 
  widget can attach resize to it. Possibly expose it as a convenience sync() method
Trigger widget that expands/collapse the container
* It may be possible to make it the same, but adds complication and restricts 
  re-usability
Widget container that expands/shrinks
* Simple animation resizing... right? Just needs a minimum size hint of (0, 0)
  Doesn't actually require a widget, should be possible on any widget (as long 
  as it hasn't had it's minimum size set)

"""


class Collapser(QtCore.QObject):
    sizeChanged = QtCore.Signal(int)

    def __init__(self, widget=None, direction=QtCore.Qt.Vertical, duration=300):
        # type: (QtWidgets.QWidget, QtCore.Qt.Orientation, int) -> None
        super(Collapser, self).__init__()
        self.widget = None
        self.direction = None

        self._animation = QtCore.QPropertyAnimation()
        self._animation.setStartValue(0)
        self._animation.setDuration(duration)
        self._is_collapsed = False

        self._animation.valueChanged.connect(self.sizeChanged.emit)

        # Initialise
        self.set_direction(direction)
        if widget is not None:
            self.set_widget(widget)

    def collapse(self):
        """ Collapses the widget. Does nothing if already collapsed """
        if self._is_collapsed or not self.widget:
            return
        self._animation.setDirection(QtCore.QAbstractAnimation.Backward)
        self._animation.start()
        self._is_collapsed = True

    def expand(self, size=None):
        # type: (int) -> None
        """ Expands the widget. Does nothing if already expanded """
        if not self._is_collapsed or not self.widget:
            return
        if size is not None:
            self._animation.setEndValue(size)
        self._animation.setDirection(QtCore.QAbstractAnimation.Forward)
        self._animation.start()
        self._is_collapsed = False

    def set_direction(self, direction):
        # type: (QtCore.Qt.Orientation) -> None
        """ Sets the direction the widget should resize """
        self.direction = direction
        anim_property = ('maximumWidth'
                         if self.direction == QtCore.Qt.Horizontal else
                         'maximumHeight')
        self._animation.setPropertyName(anim_property)

    def set_duration(self, duration):
        # type: (int) -> None
        """ Sets the duration for the animation of the widgets resizing """
        self._animation.setDuration(duration)

    def set_widget(self, widget):
        # type: (QtWidgets.QWidget) -> None
        """ Sets the widget to be resized """
        target_size = widget.sizeHint().height()
        self.widget = widget
        self._animation.setTargetObject(self.widget)
        self._animation.setEndValue(target_size)

    def toggle(self):
        # type: () -> bool
        """ Toggles the collapsed state, returns True if the widget is expanded """
        if self._is_collapsed:
            self.expand()
        else:
            self.collapse()
        return not self._is_collapsed


if __name__ == '__main__':
    import sys
    from functools import partial

    app = QtWidgets.QApplication(sys.argv)

    def debug(val):
        print(val)

    def show_collapser():
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        test_btn = QtWidgets.QPushButton('Toggle')
        test2_btn = QtWidgets.QPushButton('Expand to larger size')
        l.addWidget(test_btn)
        l.addWidget(test2_btn)
        lst = QtWidgets.QListWidget()
        col = Collapser(lst, QtCore.Qt.Horizontal)
        col.sizeChanged.connect(debug)
        test_btn.clicked.connect(col.toggle)
        test2_btn.clicked.connect(partial(col.expand, 500))
        l.addWidget(lst)
        l.addStretch()
        w.setLayout(l)
        w.show()
        return w

    def show_spoiler():
        s = Spoiler(title='Spoiler')
        b = QtWidgets.QPushButton('button')
        l = QtWidgets.QVBoxLayout()
        l.addWidget(b)
        s.setContentLayout(l)
        s.show()
        return s

    def show_spoiler_button():
        b = SpoilerButton('Spoiler')
        b.show()
        return b

    s = show_spoiler()
    sb = show_spoiler_button()
    c = show_collapser()

    app.exec_()
    sys.exit()
