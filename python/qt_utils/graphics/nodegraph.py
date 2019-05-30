from PySide2 import QtCore, QtGui, QtWidgets


class Connection(object):
    Left = 1
    Right = 2
    Both = Left | Right


class Connector(QtWidgets.QGraphicsEllipseItem):
    Radius = 7

    def __init__(self, x=0, y=0, radius=Radius):
        super(Connector, self).__init__(
            x - radius,
            y - radius,
            radius * 2,
            radius * 2,
        )
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


from itertools import zip_longest


class NodeConnector(QtWidgets.QGraphicsEllipseItem):
    Radius = 7

    def __init__(self, name, direction, x=0, y=0, radius=Radius, parent=None):
        super(NodeConnector, self).__init__(
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


class NodeItemBack(QtWidgets.QGraphicsItem):
    Width = 100
    HeaderHeight = 30
    AttrHeight = 20
    # FooterHeight = 10
    Padding = 5

    def __init__(self, name, inputs=(), outputs=(), parent=None):
        super(NodeItemBack, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        # TODO: Enable paint caching?

        self._height = (
            max(len(self.inputs), len(self.outputs)) * self.AttrHeight
            + self.HeaderHeight
            # + self.FooterHeight
        )

    def boundingRect(self):
        return QtCore.QRect(0, 0, self.Width, self._height)

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
            (rect.width() - fm.width(self.name)) * 0.5,
            fm.height(),
            self.name,
            )

        # Attributes
        offset = self.AttrHeight - (self.AttrHeight - fm.height()) * 0.5
        height = self.HeaderHeight
        # midline = self.Width // 2
        # painter.drawLine(
        #     midline,
        #     height,
        #     midline,
        #     self._height
        #     # - self.FooterHeight,
        # )
        for input_name, output_name in zip_longest(self.inputs, self.outputs):
            painter.drawLine(0, height, self.Width, height)
            if input_name == output_name:
                painter.drawText(
                    (rect.width() - fm.width(input_name)) * 0.5,
                    height + offset,
                    input_name
                )
            else:
                if input_name is not None:
                    painter.drawText(
                        self.Padding + NodeConnector.Radius,
                        height + offset,
                        input_name,
                    )
                if output_name is not None:
                    painter.drawText(
                        rect.width() - fm.width(output_name) - self.Padding - NodeConnector.Radius,
                        height + offset,
                        output_name,
                        )
            height += self.AttrHeight

        # Footer
        # painter.drawLine(0, height, self.Width, height)

        painter.restore()


class NodeItemB(QtWidgets.QGraphicsItemGroup):
    def __init__(self, name, inputs=(), outputs=(), parent=None):
        super(NodeItemB, self).__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

        self.node = NodeItemBack(name, inputs=inputs, outputs=outputs, parent=self)
        self.addToGroup(self.node)

        height = NodeItemBack.HeaderHeight + NodeItemBack.AttrHeight // 2
        for input_name, output_name in zip_longest(inputs, outputs):
            if input_name is not None:
                connector = NodeConnector(
                    input_name,
                    Connection.Left,
                    y=height,
                    parent=self,
                )
                self.addToGroup(connector)
            if output_name is not None:
                connector = NodeConnector(
                    output_name,
                    Connection.Right,
                    x=NodeItemBack.Width,
                    y=height,
                    parent=self,
                )
                self.addToGroup(connector)
            height += NodeItemBack.AttrHeight


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

        y = self.Height // 2

        self._connectors = {}
        if connection & Connection.Left:
            connector = Connector(x=0, y=y)
            self._connectors[Connection.Left] = connector
            self.addToGroup(connector)
        if connection & Connection.Right:
            connector = Connector(x=width, y=y)
            self._connectors[Connection.Right] = connector
            self.addToGroup(connector)


class NodeItemA(QtWidgets.QGraphicsItemGroup):
    Width = 100
    HeaderHeight = 30

    def __init__(self, name, inputs=(), outputs=(), bidirectional=(), parent=None):
        super(NodeItemA, self).__init__(parent)
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
            NodeItemA("NodeItemA", inputs=("one", "two"), outputs=("three",), bidirectional=("four",)),
        ]

        # ----- Widgets -----

        self.scene = QtWidgets.QGraphicsScene(self)
        for item in items:
            self.scene.addItem(item)
        self.scene.addItem(
            NodeItemB("NodeItemB", inputs=("four", "one", "two"), outputs=("four", "three",))
        )

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
