from itertools import zip_longest

from PySide2 import QtCore, QtGui, QtWidgets

from qt_utils.nodegraph import api


class PortItem(QtWidgets.QGraphicsItem):
    Radius = 6

    def __init__(self, port, parent=None):
        # type: (api.Port, QtWidgets.QGraphicsItem) -> None
        super(PortItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self._port = port

    @property
    def port(self):
        # type: () -> api.Port
        return self._port

    def boundingRect(self):
        # type: () -> QtCore.QRect
        return QtCore.QRect(
            -PortItem.Radius,
            -PortItem.Radius,
            PortItem.Radius * 2,
            PortItem.Radius * 2,
        )

    def shape(self):
        # type: () -> QtGui.QPainterPath
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionGraphicsItem , QtWidgets.QWidget) -> None
        painter.save()
        if option.state & (QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected):
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))
        painter.drawEllipse(self.boundingRect())
        painter.restore()


class _NodeItem(QtWidgets.QGraphicsItem):
    Width = 150
    HeaderHeight = 30
    AttrHeight = 20
    Padding = 5

    def __init__(self, node, parent=None):
        # type: (api.Node, QtWidgets.QGraphicsItem) -> None
        super(_NodeItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self._node = node
        # TODO: Enable paint caching?

    def boundingRect(self):
        # type: () -> QtCore.QRect
        num_attrs = max(self._node.get_input_count(), self._node.get_output_count())
        return QtCore.QRect(
            0,
            0,
            _NodeItem.Width,
            num_attrs * _NodeItem.AttrHeight + self.HeaderHeight,
        )

    def shape(self):
        # type: () -> QtGui.QPainterPath
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionGraphicsItem , QtWidgets.QWidget) -> None
        painter.save()

        if option.state & (QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected):
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))

        # Header
        rect = self.boundingRect()
        painter.drawRect(rect)

        fm = QtGui.QFontMetrics(painter.font())
        text_height = _NodeItem.HeaderHeight - (_NodeItem.HeaderHeight - fm.height()) * 0.5
        painter.drawText(
            (rect.width() - fm.width(self._node.name)) * 0.5,
            text_height,
            self._node.name,
        )

        # Attributes
        offset = _NodeItem.AttrHeight - (_NodeItem.AttrHeight - fm.height()) * 0.5
        height = _NodeItem.HeaderHeight
        for input_port, output_port in zip_longest(self._node.list_inputs(), self._node.list_outputs()):
            painter.drawLine(0, height, _NodeItem.Width, height)
            if input_port is not None:
                painter.drawText(
                    self.Padding + PortItem.Radius,
                    height + offset,
                    input_port.name,
                )
            if output_port is not None:
                painter.drawText(
                    rect.width() - fm.width(output_port.name) - _NodeItem.Padding - PortItem.Radius,
                    height + offset,
                    output_port.name,
                )
            height += _NodeItem.AttrHeight

        painter.restore()


class NodeItem(QtWidgets.QGraphicsItemGroup):
    def __init__(self, node, parent=None):
        # type: (api.Node, QtWidgets.QGraphicsItem) -> None
        super(NodeItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self._node = node

        self._item = _NodeItem(node)
        self.addToGroup(self._item)

        height = _NodeItem.HeaderHeight + _NodeItem.AttrHeight // 2
        for input_port, output_port in zip_longest(node.list_inputs(), node.list_outputs()):
            if input_port is not None:
                port = PortItem(input_port, parent=self)
                port.setPos(0, height)
                self.addToGroup(port)
            if output_port is not None:
                port = PortItem(output_port, parent=self)
                port.setPos(_NodeItem.Width, height)
                self.addToGroup(port)
            height += _NodeItem.AttrHeight

    @property
    def node(self):
        # type: () -> api.Node
        return self._node


class Widget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(Widget, self).__init__(parent)

        # ----- Widgets -----

        self.scene = QtWidgets.QGraphicsScene(self)

        node = api.Node("NodeItem")
        node.add_input_port("input_0")
        node.add_input_port("input_1")
        node.add_output_port("output_0")
        node.add_output_port("output_1")
        node.add_output_port("output_2")
        self.scene.addItem(NodeItem(node))

        self.view = QtWidgets.QGraphicsView()
        self.view.setScene(self.scene)

        # ----- Layout -----

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.view)
        self.setLayout(main_layout)

        # ----- Connections -----

        # ----- Initialise -----


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    w = Widget()
    w.show()

    app.exec_()
    sys.exit()
