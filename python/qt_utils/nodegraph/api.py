import json
import os
import re
import types
import uuid
import weakref
from collections import defaultdict


_NODE_TYPE_REGISTRY = {}


class NodeError(Exception):
    """ Errors raised with nodes """


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
    @classmethod
    def deserialize(cls, data):
        # type: (dict) -> Node
        return cls(
            data["type"],
            data["name"],
            data["identifier"],
            properties=data["properties"],
        )

    def __init__(self, node_type, name, identifier, properties=None):
        # type: (str, str, str, dict) -> None
        self._name = name
        self._type = node_type
        self._inputs = []
        self._outputs = []
        self._identifier = identifier
        self._properties = properties or {}

    def __repr__(self):
        return "{}({!r}, {!r}, {!r}, properties={!r})".format(
            self.__class__.__name__,
            self._type,
            self._name,
            self._identifier,
            self._properties,
        )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.identifier == self._identifier
        )

    def __hash__(self):
        return hash(self._identifier)

    def __getitem__(self, item):
        return self._properties[item]

    def __setitem__(self, key, value):
        if key not in self._properties:
            raise KeyError("Invalid property {!r} for node {}".format(key, self._name))
        self._properties[key] = value

    @property
    def identifier(self):
        # type: () -> str
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
        # type: () -> list[tuple[Port, Port]]
        connections = []
        for port in self._inputs:
            for i in range(port.get_connection_count()):
                connections.append((port, port.get_connected_by_index(i)))
        for port in self._outputs:
            for i in range(port.get_connection_count()):
                connections.append((port.get_connected_by_index(i), port))
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

    def serialize(self):
        # type: () -> dict
        return {
            "name": self._name,
            "type": self._type,
            "identifier": self._identifier,
            "properties": self._properties,
        }

    def type(self):
        # type: () -> str
        return self._type


class Scene(object):
    @classmethod
    def deserialize(cls, data):
        # type: (dict) -> Scene
        nodes = {}
        for node_data in data["nodes"]:
            node_class = get_registered_node_type(node_data["type"])
            node = node_class.deserialize(node_data)
            nodes[node.identifier] = node

        for source_identifier, connections in data["connections"].items():
            source = nodes[source_identifier]
            for input_name, target_identifier, output_name in connections:
                target = nodes[target_identifier]
                in_port = source.get_input_by_name(input_name)
                out_port = target.get_output_by_name(output_name)
                in_port.connect(out_port)

        return cls(list(nodes.values()))

    @classmethod
    def load(cls, filepath):
        # type: (str) -> Scene
        with open(filepath) as f:
            data = json.load(f)
        return cls.deserialize(data)

    def __init__(self, nodes=()):
        # type: (list[Node]) -> None
        self._identifiers = {n.identifier: n for n in nodes}
        self._names = weakref.WeakValueDictionary({n.name: n for n in nodes})

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

        node_class = _NODE_TYPE_REGISTRY[node_type]

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

    def save(self, filepath):
        # type: (str) -> None
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

        data = self.serialize()
        with open(filepath, "w") as f:
            json.dump(data, f)

    def serialize(self):
        # type: () -> dict
        connections = defaultdict(set)
        for node in self._identifiers.values():
            for source, target in node.list_connections():
                connections[source.node.identifier].add(
                    (source.name, target.node.identifier, target.name)
                )

        return {
            "nodes": [n.serialize() for n in self._identifiers.values()],
            "connections": {
                identifier: list(c) for identifier, c in connections.items()
            },
        }


def get_registered_node_type(node_type):
    # type: (str) -> types.Type[Node]
    return _NODE_TYPE_REGISTRY[node_type]


def register_node_type(node_type, node_class):
    # type: (str, types.Type[Node]) -> None
    if node_type in _NODE_TYPE_REGISTRY:
        raise ValueError("Node type already registered: {}".format(node_type))
    if Node not in node_class.mro():
        raise TypeError("Node class must inherit from Node")
    _NODE_TYPE_REGISTRY[node_type] = node_class


register_node_type("Node", Node)


if __name__ == '__main__':
    class EntityNode(Node):
        Type = "Entity"

        def __init__(self, node_type, name, identifier, properties=None):
            defaults = {"key": 5}
            if properties is not None:
                defaults.update(properties)
            super(EntityNode, self).__init__(
                node_type, name, identifier, properties=defaults,
            )
            self.add_input_port("inputs")
            self.add_output_port("outputs")

    register_node_type(EntityNode.Type, EntityNode)

    s = Scene()
    n1 = s.create_node(EntityNode.Type, "one")
    n1["key"] = 10
    print(n1)
    n2 = s.create_node(EntityNode.Type, "one")
    print(n2)
    print(s.list_nodes())
    print(s.list_nodes(node_type="Node"))
    print(s.list_nodes(node_type=EntityNode.Type))

    n1.get_output_by_index(0).connect(n2.get_input_by_index(0))

    path = r"C:\Users\Matthew\Documents\temp\qt_utils\scene.json"
    s.save(path)
    s2 = Scene.load(path)
    print(s2.list_nodes())
