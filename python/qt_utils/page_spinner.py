from PySide2 import QtCore, QtGui, QtWidgets


class PageStyle(QtWidgets.QCommonStyle):
    def draw_spin_box_button(self, sub_control, option, painter):
        painter.save()

        # Button
        button_opt = QtWidgets.QStyleOption(option)
        button_opt.rect = self.subControlRect(self.CC_SpinBox, option, sub_control)
        if not (option.activeSubControls & sub_control):
            button_opt.state &= ~(self.State_MouseOver | self.State_On | self.State_Sunken)
        self.drawPrimitive(self.PE_FrameButtonBevel, button_opt, painter)

        # Icon
        button_opt.rect.adjust(3, 3, -3, -3)
        if button_opt.rect.isValid():
            if sub_control == self.SC_SpinBoxUp or option.direction == QtCore.Qt.RightToLeft:
                arrow = self.PE_IndicatorArrowRight
            else:
                arrow = self.PE_IndicatorArrowLeft
            self.drawPrimitive(arrow, button_opt, painter)

        painter.restore()

    def drawComplexControl(self, which, option, painter, widget):
        if which == self.CC_SpinBox:
            self.draw_spin_box_button(self.SC_SpinBoxDown, option, painter)
            self.draw_spin_box_button(self.SC_SpinBoxUp, option, painter)
        else:
            return super(PageStyle, self).drawComplexControl(which, option, painter, widget)

    def subControlRect(self, control, option, sub_control, widget=None):
        if control == self.CC_SpinBox:
            frame_width = self.pixelMetric(self.PM_DefaultFrameWidth, option, widget)
            button_width = 16

            if sub_control == self.SC_SpinBoxFrame:
                return option.rect
            elif sub_control == self.SC_SpinBoxEditField:
                return option.rect.adjusted(+button_width, +frame_width,
                                            -button_width, -frame_width)
            elif sub_control == self.SC_SpinBoxDown:
                return self.visualRect(option.direction, option.rect,
                                       QtCore.QRect(option.rect.x(), option.rect.y(),
                                                    button_width,
                                                    option.rect.height()))
            elif sub_control == self.SC_SpinBoxUp:
                return self.visualRect(option.direction, option.rect,
                                       QtCore.QRect(option.rect.right() - button_width,
                                                    option.rect.y(),
                                                    button_width,
                                                    option.rect.height()))
            else:
                return QtCore.QRect()
        else:
            return super(PageStyle, self).subControlRect(control, option,
                                                         sub_control,
                                                         widget)


class PageSpinner(QtWidgets.QWidget):
    pageChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(PageSpinner, self).__init__(parent)

        # Widgets
        self._spinner = QtWidgets.QSpinBox()
        self._spinner.setAlignment(QtCore.Qt.AlignCenter)
        self._spinner.setStyle(PageStyle())

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._spinner)
        layout.setContentsMargins(0, 0, 0, 0)

        # Connections
        self._spinner.valueChanged.connect(self.pageChanged.emit)

        # Initialise
        self.set_max_page(0)

    @property
    def current_page(self):
        # type: () -> int
        return self._spinner.value()

    @property
    def max_page(self):
        # type: () -> int
        return self._spinner.maximum()

    def set_current_page(self, page):
        # type: (int) -> bool
        if not (0 <= page <= self._spinner.maximum()):
            return False
        self._spinner.setValue(page)
        return True

    def set_max_page(self, max_page):
        # type: (int) -> None
        self._spinner.setMaximum(max_page)
        self._spinner.setSuffix(' / {}'.format(max_page))
        self._spinner.setMinimum(1 if max_page > 0 else 0)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    def debug(page):
        print('Page changed:', page)

    ps = PageSpinner()
    ps.pageChanged.connect(debug)
    ps.set_max_page(5)
    ps.show()

    pages = [0, 5, 10]
    btn = QtWidgets.QPushButton('Toggle')
    btn.clicked.connect(lambda: ps.set_max_page(pages[(pages.index(ps.max_page) + 1) % len(pages)]))
    btn.show()

    app.exec_()
    sys.exit()
