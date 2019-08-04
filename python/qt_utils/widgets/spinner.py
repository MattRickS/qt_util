import math

from PySide2 import QtCore, QtGui, QtWidgets


class Spinner(QtWidgets.QWidget):
    def __init__(self, parent=None, colour=None, disable_parent=True):
        super(Spinner, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._count = 12
        self._current = 0
        self._disable_parent = disable_parent
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.rotate)

        # Appearance
        self._colour = QtGui.QColor(colour or "black")
        self._fade = 80.0
        self._inner_radius = 10
        self._line_length = 10
        self._line_width = 2
        self._min_opacity = 15
        self._revolutions_per_second = 1.5
        self._roundness = 75.0

        self.update_size()
        self.update_speed()
        self.hide()

    @property
    def colour(self):
        return self._colour

    @colour.setter
    def colour(self, value):
        self._colour = value

    @property
    def fade(self):
        return self._fade

    @fade.setter
    def fade(self, value):
        self._fade = min(100.0, max(0.0, value))

    @property
    def inner_radius(self):
        return self._inner_radius

    @inner_radius.setter
    def inner_radius(self, value):
        self._inner_radius = value
        self.update_size()

    @property
    def line_length(self):
        return self._line_length

    @line_length.setter
    def line_length(self, value):
        self._line_length = value
        self.update_size()

    @property
    def line_width(self):
        return self._line_width

    @line_width.setter
    def line_width(self, value):
        self._line_width = value

    @property
    def min_opacity(self):
        return self._min_opacity

    @min_opacity.setter
    def min_opacity(self, value):
        if isinstance(value, float):
            value = int(value * 255)
        self._min_opacity = min(255, max(0, value))

    @property
    def num_lines(self):
        return self._count

    @num_lines.setter
    def num_lines(self, value):
        self._count = value
        self._current = 0
        self.update_speed()

    @property
    def roundness(self):
        return self._roundness

    @roundness.setter
    def roundness(self, value):
        self._roundness = min(100.0, max(0.0, value))

    @property
    def speed(self):
        return self._revolutions_per_second

    @speed.setter
    def speed(self, value):
        self._revolutions_per_second = value
        self.update_speed()

    def get_line_color(self, i):
        distance = (self._current - i) % self._count
        if distance <= 0:
            return self._colour

        colour = QtGui.QColor(self._colour)
        distance_threshold = int(math.ceil((self._count - 1) * self._fade / 100.0))
        if distance > distance_threshold:
            colour.setAlpha(self._min_opacity)
        else:
            alpha_diff = colour.alpha() - self._min_opacity
            gradient = alpha_diff / float(distance_threshold + 1)
            result_alpha = colour.alpha() - gradient * distance

            # If alpha is out of bounds, clip it.
            result_alpha = min(255, max(0, result_alpha))
            colour.setAlpha(result_alpha)

        return colour

    def is_spinning(self):
        return self._timer.isActive()

    def rotate(self):
        self._current = (self._current + 1) % self._count
        self.update()

    def start(self):
        self.show()

        if self.parentWidget() and self._disable_parent:
            self.parentWidget().setEnabled(False)

        if not self._timer.isActive():
            self._timer.start()
            self._current = 0

    def stop(self):
        self.hide()

        if self.parentWidget() and self._disable_parent:
            self.parentWidget().setEnabled(True)

        if self._timer.isActive():
            self._timer.stop()
            self._current = 0

    def update_position(self):
        if not self.parentWidget():
            return
        self.move(
            self.parentWidget().width() / 2 - self.width() / 2,
            self.parentWidget().height() / 2 - self.height() / 2,
        )

    def update_size(self):
        size = (self._inner_radius + self._line_length) * 2
        self.setFixedSize(size, size)

    def update_speed(self):
        self._timer.setInterval(1000 / (self._count * self._revolutions_per_second))

    def paintEvent(self, event):
        self.update_position()
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtCore.Qt.transparent)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.NoPen)

        line_rect = QtCore.QRect(
            0, -self._line_width / 2, self._line_length, self._line_width
        )
        for i in range(self._count):
            painter.save()
            painter.translate(
                self._inner_radius + self._line_length,
                self._inner_radius + self._line_length,
            )
            rotate_angle = (360 * i) / float(self._count)
            painter.rotate(rotate_angle)
            painter.translate(self._inner_radius, 0)

            color = self.get_line_color(i)
            painter.setBrush(color)
            painter.drawRoundedRect(
                line_rect, self._roundness, self._roundness, QtCore.Qt.RelativeSize
            )
            painter.restore()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    btn = QtWidgets.QPushButton("btn")
    btn.show()
    btn.resize(100, 100)

    w = Spinner(btn, disable_parent=False)
    w.show()
    w.start()

    colours = list(map(QtGui.QColor, ("red", "green", "blue", "black")))

    def cycle_colour():
        index = colours.index(w.colour)
        index = (index + 1) % len(colours)
        w.colour = colours[index]

    btn.clicked.connect(cycle_colour)

    app.exec_()
    sys.exit()
