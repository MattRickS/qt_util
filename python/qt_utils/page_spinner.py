from PySide2 import QtCore, QtGui, QtWidgets


class PageStyle(QtWidgets.QCommonStyle):
    BUTTON_WIDTH = 16

    def draw_spin_box_button(self, sub_control, option, painter):
        painter.save()

        # Button
        button_opt = QtWidgets.QStyleOption(option)
        button_opt.rect = self.subControlRect(self.CC_SpinBox, option, sub_control)
        if not (option.activeSubControls & sub_control):
            button_opt.state &= ~(self.State_MouseOver | self.State_On | self.State_Sunken)
        self.drawPrimitive(self.PE_PanelButtonBevel, button_opt, painter)

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

            if sub_control == self.SC_SpinBoxFrame:
                return option.rect
            elif sub_control == self.SC_SpinBoxEditField:
                return option.rect.adjusted(self.BUTTON_WIDTH, frame_width,
                                            -self.BUTTON_WIDTH, -frame_width)
            elif sub_control == self.SC_SpinBoxDown:
                return self.visualRect(option.direction, option.rect,
                                       QtCore.QRect(option.rect.x(),
                                                    option.rect.y(),
                                                    self.BUTTON_WIDTH,
                                                    option.rect.height()))
            elif sub_control == self.SC_SpinBoxUp:
                return self.visualRect(option.direction, option.rect,
                                       QtCore.QRect(option.rect.right() - self.BUTTON_WIDTH,
                                                    option.rect.y(),
                                                    self.BUTTON_WIDTH,
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
        self._spinner.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                    QtWidgets.QSizePolicy.Expanding)

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
        opt = QtWidgets.QStyleOptionSpinBox()
        opt.initFrom(self._spinner)
        margin = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth, opt, self)
        text_width = self.fontMetrics().width('{} / {}'.format(max_page, max_page))
        width = text_width + PageStyle.BUTTON_WIDTH * 2 + margin * 4
        self.setMinimumWidth(width)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    def debug(page):
        print('Page changed:', page)

    ps = PageSpinner()
    ps.pageChanged.connect(debug)
    ps.set_max_page(5)
    ps.show()

    pages = [0, 5, 100]
    btn = QtWidgets.QPushButton('Toggle')
    btn.clicked.connect(lambda: ps.set_max_page(pages[(pages.index(ps.max_page) + 1) % len(pages)]))
    btn.show()

    app.exec_()
    sys.exit()
