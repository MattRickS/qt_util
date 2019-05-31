import re
import types


NODE_TYPES = {}


class Port(object):
    def __init__(self, node, name):
        # type: (Node, str) -> None
        self._node = node
        self._name = name
        self._connected = []

    def __repr__(self):
        return "{}({!r}, {!r})".format(self.__class__.__name__, self._node, self._name)

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def node(self):
        # type: () -> Node
        return self._node

    def connect(self, port):
        # type: (Port) -> None
        if port in self._connected:
            return
        if port.node == self:
            raise ValueError("Cannot connect a port to it's own node")
        self._connected.append(port)
        port._connected.append(self)

    def get_connected_by_index(self, index):
        # type: (int) -> Port
        return self._connected[index]

    def get_connection_count(self):
        # type: () -> int
        return len(self._connected)


class Node(object):
    def __init__(self, node_type, name):
        # type: (str, str) -> None
        self._name = name
        self._type = node_type
        self._inputs = []
        self._outputs = []

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        # type: () -> str
        return self._name

    def add_input_port(self, name):
        # type: (str) -> Port
        port = Port(self, name)
        self._inputs.append(port)
        return port

    def add_output_port(self, name):
        # type: (str) -> Port
        port = Port(self, name)
        self._outputs.append(port)
        return port

    def get_input_by_index(self, index):
        # type: (int) -> Port
        return self._inputs[index]

    def get_input_by_name(self, name):
        # type: (str) -> Port
        for port in self._inputs:
            if port.name == name:
                return port
        raise KeyError("Node {!r} has no port named {!r}".format(self._name, name))

    def get_input_count(self):
        # type: () -> int
        return len(self._inputs)

    def get_output_count(self):
        # type: () -> int
        return len(self._outputs)

    def get_output_by_index(self, index):
        # type: (int) -> Port
        return self._outputs[index]

    def get_output_by_name(self, name):
        # type: (str) -> Port
        for port in self._outputs:
            if port.name == name:
                return port
        raise KeyError("Node {!r} has no port named {!r}".format(self._name, name))

    def list_inputs(self):
        # type: () -> list[str]
        return self._inputs[:]

    def list_outputs(self):
        # type: () -> list[str]
        return self._outputs[:]

    def remove_input_port(self, port):
        # type: (Port) -> None
        self._inputs.remove(port)

    def remove_output_port(self, port):
        # type: (Port) -> None
        self._outputs.remove(port)

    def type(self):
        # type: () -> str
        return self._type


class Scene(object):
    def __init__(self):
        self._nodes = {}

    def create_node(self, node_type, name):
        # type: (str, str) -> Node
        node_class = NODE_TYPES[node_type]

        # Scan for existing names and increment the number
        num = -1
        pattern = "^{}(\d+)?$".format(name)
        for node_name in self._nodes.keys():
            match = re.match(pattern, node_name)
            if match:
                num = max(num, int(match.group(1) or 0))

        if num > -1:
            name = "{}{}".format(name, num + 1)

        node = node_class(node_type, name)
        self._nodes[name] = node
        return node

    def get_node(self, name):
        # type: (str) -> Node
        return self._nodes[name]

    def list_nodes(self, node_type=None):
        # type: (str) -> list[Node]
        if node_type is not None:
            return [node for node in self._nodes.values() if node.type() == node_type]
        else:
            return list(self._nodes.values())


def register_node_type(node_type, node_class):
    # type: (str, types.Type[Node]) -> None
    if node_type in NODE_TYPES:
        raise ValueError("Node type already registered: {}".format(node_type))
    if Node not in node_class.mro():
        raise TypeError("Node class must inherit from Node")
    NODE_TYPES[node_type] = node_class


register_node_type("Node", Node)


if __name__ == '__main__':
    class EntityNode(Node):
        Type = "Entity"

        def __init__(self, node_type, name):
            super(EntityNode, self).__init__(node_type, name)
            self.add_input_port("inputs")
            self.add_output_port("used")

    register_node_type(EntityNode.Type, EntityNode)

    # n1 = Node("one")
    # n1.add_input_port("i1")
    # n1.add_input_port("i2")
    # n1.add_output_port("o1")
    #
    # n2 = Node("two")
    # n2.add_input_port("i1")
    # n2.add_output_port("o1")
    #
    # p1 = n1.get_output_by_index(0)
    # p2 = n2.get_input_by_name("i1")
    # p1.connect(p2)
    #
    # print(n1)
    # print(p1)
    # print(p2)
    # print(n2)

    s = Scene()
    n = s.create_node(EntityNode.Type, "one")
    print(n)
    n = s.create_node(EntityNode.Type, "one")
    print(n)
