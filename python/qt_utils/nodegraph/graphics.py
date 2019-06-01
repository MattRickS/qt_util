from itertools import zip_longest

from PySide2 import QtCore, QtGui, QtWidgets

from qt_utils.nodegraph import api


FLAG_STATES = QtWidgets.QStyle.State_MouseOver | QtWidgets.QStyle.State_Selected


class PortItem(QtWidgets.QGraphicsItem):
    Radius = 7

    def __init__(self, port, parent=None):
        # type: (api.Port, QtWidgets.QGraphicsItem) -> None
        super(PortItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self._port = port
        self._drag_over = False

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
        if self._drag_over:
            colour = QtGui.QColor("#FFFFDD")
        elif option.state & FLAG_STATES:
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))
        painter.drawEllipse(self.boundingRect())
        painter.restore()

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        direction = str(mime.data("direction"))
        if direction.isdigit() and int(direction) != self._port.direction:
            event.setAccepted(True)
            self._drag_over = True
            self.update()
        else:
            event.setAccepted(False)

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self.update()

    def dropEvent(self, event):
        node_scene = self.scene().node_scene

        mime = event.mimeData()
        node_name = str(mime.data("node"))
        port_name = str(mime.data("port"))
        # PySide2 uses it's own ByteArray object, cast to str to cast to int
        direction = int(str(mime.data("direction")))

        node = node_scene.get_node(node_name)
        if direction == api.Port.Input:
            port = node.get_input_by_name(port_name)
        else:
            port = node.get_output_by_name(port_name)

        self._port.connect(port)
        self._drag_over = False
        self.update()

    def mousePressEvent(self, event):
        self.setCursor(QtCore.Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if QtCore.QLineF(event.screenPos(), event.buttonDownScreenPos(QtCore.Qt.LeftButton)).length() < QtWidgets.QApplication.startDragDistance():
            return

        drag = QtGui.QDrag(event.widget())
        mime = QtCore.QMimeData()
        mime.setData("node", self._port.node.name)
        mime.setData("port", self._port.name)
        mime.setData("direction", str(self._port.direction))

        drag.setMimeData(mime)
        drag.exec_()
        self.setCursor(QtCore.Qt.OpenHandCursor)


class NodeItem(QtWidgets.QGraphicsItem):
    Width = 150
    HeaderHeight = 30
    AttrHeight = 20
    Padding = 5

    def __init__(self, node, parent=None):
        # type: (api.Node, QtWidgets.QGraphicsItem) -> None
        super(NodeItem, self).__init__(parent)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self._node = node
        # TODO: Enable paint caching?

        height = NodeItem.HeaderHeight + NodeItem.AttrHeight // 2
        inputs, outputs = node.list_inputs(), node.list_outputs()
        for input_port, output_port in zip_longest(inputs, outputs):
            if input_port is not None:
                port = PortItem(input_port, parent=self)
                port.setPos(0, height)
            if output_port is not None:
                port = PortItem(output_port, parent=self)
                port.setPos(NodeItem.Width, height)
            height += NodeItem.AttrHeight

    @property
    def node(self):
        # type: () -> api.Node
        return self._node

    def boundingRect(self):
        # type: () -> QtCore.QRect
        num_attrs = max(self._node.get_input_count(), self._node.get_output_count())
        return QtCore.QRect(
            0,
            0,
            NodeItem.Width,
            num_attrs * NodeItem.AttrHeight + self.HeaderHeight,
        )

    def shape(self):
        # type: () -> QtGui.QPainterPath
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        # type: (QtGui.QPainter, QtWidgets.QStyleOptionGraphicsItem , QtWidgets.QWidget) -> None
        painter.save()

        if option.state & FLAG_STATES:
            colour = QtGui.QColor("#FFDDDD")
        else:
            colour = QtGui.QColor("#DDFFDD")
        painter.setBrush(QtGui.QBrush(colour))

        # Header
        rect = self.boundingRect()
        painter.drawRect(rect)

        fm = QtGui.QFontMetrics(painter.font())
        text_height = NodeItem.HeaderHeight - (NodeItem.HeaderHeight - fm.height()) * 0.5
        painter.drawText(
            (rect.width() - fm.width(self._node.name)) * 0.5,
            text_height,
            self._node.name,
        )

        # Attributes
        height = NodeItem.HeaderHeight
        height_offset = NodeItem.AttrHeight - (NodeItem.AttrHeight - fm.height()) * 0.5
        output_offset = rect.width() - NodeItem.Padding - PortItem.Radius
        inputs, outputs = self._node.list_inputs(), self._node.list_outputs()
        for input_port, output_port in zip_longest(inputs, outputs):
            painter.drawLine(0, height, NodeItem.Width, height)
            if input_port is not None:
                painter.drawText(
                    self.Padding + PortItem.Radius,
                    height + height_offset,
                    input_port.name,
                )
            if output_port is not None:
                painter.drawText(
                    output_offset - fm.width(output_port.name),
                    height + height_offset,
                    output_port.name,
                )
            height += NodeItem.AttrHeight

        painter.restore()


class GraphicsNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self, node_scene, parent=None):
        super(GraphicsNodeScene, self).__init__(parent)
        self._node_scene = node_scene
        for node in self._node_scene.list_nodes():
            self.addItem(NodeItem(node))

    @property
    def node_scene(self):
        # type: () -> api.Scene
        return self._node_scene


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    scene = api.Scene()

    n1 = scene.create_node("Node", "NodeItem1")
    n1.add_input_port("one")
    n1.add_input_port("two")
    n1.add_output_port("three")

    n2 = scene.create_node("Node", "NodeItem2")
    n2.add_input_port("one")
    n2.add_output_port("two")

    graphics_scene = GraphicsNodeScene(scene)
    w = QtWidgets.QGraphicsView(graphics_scene)
    w.show()

    app.exec_()
    sys.exit()
