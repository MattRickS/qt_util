from PySide2 import QtCore, QtGui, QtWidgets

MARGIN = 2


class FilterHeader(QtWidgets.QHeaderView):
    def __init__(self, parent=None):
        super(FilterHeader, self).__init__(QtCore.Qt.Horizontal, parent)
        self.sectionResized.connect(self.handleSectionResized)
        self.sectionMoved.connect(self.handleSectionMoved)
        self.setSectionsClickable(True)
        self.setHighlightSections(True)
        self.setSectionsMovable(True)
        self.setDefaultAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.boxes = []

    def sizeHint(self):
        size = super(FilterHeader, self).size()
        return QtCore.QSize(size.width(), 50)

    def showEvent(self, event):
        self.boxes = []
        for i in range(self.count()):
            widget = QtWidgets.QLineEdit(self)
            widget.setGeometry(self.get_widget_geometry(i))
            widget.show()
            self.boxes.append(widget)
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

    def handleSectionResized(self, logical_index):
        for i in range(self.visualIndex(logical_index), self.count()):
            logical = self.logicalIndex(i)
            self.boxes[logical].setGeometry(self.get_widget_geometry(logical))

    def handleSectionMoved(self, logical, old_visual_index, new_visual_index):
        for i in range(min(old_visual_index, new_visual_index), self.count()):
            logical = self.logicalIndex(i)
            self.boxes[logical].setGeometry(self.get_widget_geometry(logical))

    # Fuck

    def fixComboPositions(self):
        for i in range(self.count()):
            self.boxes[i].setGeometry(self.get_widget_geometry(i))


class View(QtWidgets.QTableView):
    def scrollContentsBy(self, dx, dy):
        super(View, self).scrollContentsBy(dx, dy)
        hheader = self.horizontalHeader()
        if dx != 0:
            hheader.fixComboPositions()


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
