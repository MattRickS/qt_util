from PySide2 import QtCore, QtGui, QtWidgets


class Connection(object):
    Left = 1
    Right = 2
    Both = Left | Right


class Connector(QtWidgets.QGraphicsEllipseItem):
    Radius = 7

    def __init__(self, x=0, y=0, size=Radius*2):
        super(Connector, self).__init__(x, y, size, size)
        self.setAcceptHoverEvents(True)

    def paint(self, painter, option, widget):
        painter.save()
        if option.state & (QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected):
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))
        painter.drawEllipse(self.boundingRect())
        painter.restore()


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


class Attribute(QtWidgets.QGraphicsItemGroup):
    Height = 20

    def __init__(self, name, width, connection, parent=None):
        super(Attribute, self).__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

        self._text_box = TextBox(
            name,
            QtCore.QRect(0, 0, width, self.Height),
            alignment=connection,
            padding=TextBox.Padding + Connector.Radius,
        )
        self.addToGroup(self._text_box)

        y = int((self.Height - Connector.Radius * 2) * 0.5)

        self._connectors = {}
        if connection & Connection.Left:
            connector = Connector(x=-Connector.Radius, y=y)
            self._connectors[Connection.Left] = connector
            self.addToGroup(connector)
        if connection & Connection.Right:
            connector = Connector(x=width - Connector.Radius, y=y)
            self._connectors[Connection.Right] = connector
            self.addToGroup(connector)


class NodeItem(QtWidgets.QGraphicsItemGroup):
    Width = 100
    HeaderHeight = 30

    def __init__(self, name, inputs=(), outputs=(), bidirectional=(), parent=None):
        super(NodeItem, self).__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

        self._header = TextBox(name, QtCore.QRect(0, 0, self.Width, self.HeaderHeight))
        self.addToGroup(self._header)

        height = self.y() + self.HeaderHeight

        x = self.x()
        for attr_list, connection in zip(
                (inputs, outputs, bidirectional),
                (Connection.Left, Connection.Right, Connection.Both)
        ):
            for attr_name in attr_list:
                attr = Attribute(attr_name, self.Width, connection, parent=self)
                attr.setPos(x, height)
                self.addToGroup(attr)
                height += Attribute.Height


class Widget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(Widget, self).__init__(parent)

        items = [
            NodeItem("NodeA", inputs=("one", "two"), outputs=("three",), bidirectional=("four",)),
        ]

        # ----- Widgets -----

        self.scene = QtWidgets.QGraphicsScene(self)
        for item in items:
            self.scene.addItem(item)

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
