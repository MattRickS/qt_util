from itertools import zip_longest

from PySide2 import QtCore, QtGui, QtWidgets

from qt_utils.graphics import api


class Connection(object):
    Left = 1
    Right = 2
    Both = Left | Right


class PortItem(QtWidgets.QGraphicsEllipseItem):
    Radius = 6

    def __init__(self, name, direction, x=0, y=0, radius=Radius, parent=None):
        super(PortItem, self).__init__(
            x - radius,
            y - radius,
            radius * 2,
            radius * 2,
            parent
        )
        self.setAcceptHoverEvents(True)
        self.name = name
        self.direction = direction

    def paint(self, painter, option, widget):
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
        super(_NodeItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self._node = node
        # TODO: Enable paint caching?

        self._height = (
                max(node.get_input_count(), node.get_output_count()) * _NodeItem.AttrHeight
                + self.HeaderHeight
        )

    def boundingRect(self):
        return QtCore.QRect(0, 0, _NodeItem.Width, self._height)

    def shape(self):
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
        painter.drawText(
            (rect.width() - fm.width(self._node.name)) * 0.5,
            fm.height(),
            self._node.name,
            )

        # Attributes
        offset = _NodeItem.AttrHeight - (_NodeItem.AttrHeight - fm.height()) * 0.5
        height = _NodeItem.HeaderHeight
        for input_name, output_name in zip_longest(self._node.list_inputs(), self._node.list_outputs()):
            painter.drawLine(0, height, _NodeItem.Width, height)
            if input_name is not None:
                painter.drawText(
                    self.Padding + PortItem.Radius,
                    height + offset,
                    input_name,
                )
            if output_name is not None:
                painter.drawText(
                    rect.width() - fm.width(output_name) - _NodeItem.Padding - PortItem.Radius,
                    height + offset,
                    output_name,
                    )
            height += _NodeItem.AttrHeight

        painter.restore()


class NodeItem(QtWidgets.QGraphicsItemGroup):
    def __init__(self, node, parent=None):
        super(NodeItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self._node = node

        self._item = _NodeItem(node)
        self.addToGroup(self._item)

        height = _NodeItem.HeaderHeight + _NodeItem.AttrHeight // 2
        for input_name, output_name in zip_longest(node.list_inputs(), node.list_outputs()):
            if input_name is not None:
                connector = PortItem(
                    input_name,
                    Connection.Left,
                    y=height,
                    parent=self,
                )
                self.addToGroup(connector)
            if output_name is not None:
                connector = PortItem(
                    output_name,
                    Connection.Right,
                    x=_NodeItem.Width,
                    y=height,
                    parent=self,
                )
                self.addToGroup(connector)
            height += _NodeItem.AttrHeight

    @property
    def node(self):
        return self._node


class TextBox(QtWidgets.QGraphicsRectItem):
    Padding = 5

    def __init__(self, name, rect, alignment=Connection.Both, padding=Padding):
        super(TextBox, self).__init__(rect)
        self.setAcceptHoverEvents(True)
        self.name = name
        self._alignment = alignment
        self._padding = padding

    def paint(self, painter, option, widget):
        painter.save()
        if option.state & (QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected):
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))

        rect = self.boundingRect()
        painter.drawRect(rect)

        fm = QtGui.QFontMetrics(painter.font())
        if self._alignment == Connection.Left:
            width = self._padding
        elif self._alignment == Connection.Right:
            width = rect.width() - fm.width(self.name) - self._padding
        elif self._alignment == Connection.Both:
            width = (rect.width() - fm.width(self.name)) * 0.5
        else:
            raise ValueError("Invalid connection type: {}".format(self._alignment))
        painter.drawText(width, fm.height(), self.name)

        painter.restore()


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
        node.add_output_port("output_3")
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
