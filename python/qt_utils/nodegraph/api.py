import re
import types
import uuid
import weakref

NODE_TYPES = {}


class NodeError(Exception):
    """ Errors raised with nodes """


class Connection(object):
    def __init__(self, source, target):
        # type: (Port, Port) -> None
        self._source = source
        self._target = target

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self._source, self._target)

    def __str__(self):
        return "{}<->{}".format(self._source, self._target)

    def __eq__(self, other):
        return (
            isinstance(other, Connection)
            and ((self._source == other.source and self._target == other.target)
                 or (self._source == other.target and self._target == other.source))
        )

    def __hash__(self):
        return hash(self._source) | hash(self._target)

    @property
    def source(self):
        # type: () -> Port
        return self._source

    @property
    def target(self):
        # type: () -> Port
        return self._target


class Port(object):
    Output = 0
    Input = 1

    def __init__(self, node, name, direction):
        # type: (Node, str, int) -> None
        self._direction = direction
        self._node = node
        self._name = name
        self._connected = []

    def __repr__(self):
        return "{}({!r}, {!r})".format(self.__class__.__name__, self._node, self._name)

    def __str__(self):
        return "{}.{}".format(self.node.name, self._name)

    @property
    def direction(self):
        # type: () -> int
        return self._direction

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
    def __init__(self, node_type, name, identifier):
        # type: (str, str, object) -> None
        self._name = name
        self._type = node_type
        self._inputs = []
        self._outputs = []
        self._identifier = identifier

    def __repr__(self):
        return "{}({!r}, {!r}, {!r})".format(
            self.__class__.__name__,
            self._type,
            self._name,
            self._identifier,
        )

    @property
    def identifier(self):
        return self._identifier

    @property
    def name(self):
        # type: () -> str
        return self._name

    def add_input_port(self, name):
        # type: (str) -> Port
        port = Port(self, name, Port.Input)
        self._inputs.append(port)
        return port

    def add_output_port(self, name):
        # type: (str) -> Port
        port = Port(self, name, Port.Output)
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

    def list_connections(self):
        connections = []
        for port in self._inputs + self._outputs:
            for i in range(port.get_connection_count()):
                connection = Connection(port, port.get_connected_by_index(i))
                connections.append(connection)
        return connections

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
        self._identifiers = {}
        self._names = weakref.WeakValueDictionary()

    def create_node(self, node_type, name, identifier=None):
        # type: (str, str, str) -> Node
        if identifier is None:
            identifier = uuid.uuid4().hex
        elif not isinstance(identifier, str):
            raise NodeError(
                "Identifier must be str, not {}".format(type(identifier))
            )

        if identifier in self._identifiers:
            raise NodeError(
                "Node with identifier {} already exists".format(identifier)
            )

        node_class = NODE_TYPES[node_type]

        # Scan for existing names and increment the number
        num = -1
        pattern = "^{}(\d+)?$".format(name)
        for node_name in self._names.keys():
            match = re.match(pattern, node_name)
            if match:
                num = max(num, int(match.group(1) or 0))

        if num > -1:
            name = "{}{}".format(name, num + 1)

        node = node_class(node_type, name, identifier=identifier)
        self._names[name] = node
        self._identifiers[identifier] = node
        return node

    def get_node_by_identifier(self, identifier):
        # type: (str) -> Node
        return self._identifiers[identifier]

    def get_node_by_name(self, name):
        # type: (str) -> Node
        return self._names[name]

    def list_nodes(self, node_type=None):
        # type: (str) -> list[Node]
        if node_type is not None:
            return [node for node in self._names.values() if node.type() == node_type]
        else:
            return list(self._names.values())

    def remove_node(self, node):
        # type: (Node) -> None
        self._names.pop(node.name)
        self._identifiers.pop(node.identifier)


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

        def __init__(self, node_type, name, identifier=None):
            super(EntityNode, self).__init__(node_type, name, identifier=identifier)
            self.add_input_port("inputs")
            self.add_output_port("used")

    register_node_type(EntityNode.Type, EntityNode)

    s = Scene()
    n = s.create_node(EntityNode.Type, "one")
    print(n)
    n = s.create_node("Node", "one")
    print(n)
    print(s.list_nodes())
    print(s.list_nodes(node_type="Node"))
    print(s.list_nodes(node_type=EntityNode.Type))
