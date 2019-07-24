from PySide2 import QtCore, QtGui, QtWidgets


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        super(ClickableLabel, self).mousePressEvent(event)
        self.clicked.emit()
