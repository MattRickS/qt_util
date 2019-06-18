import json
import re
import types


_NODE_TYPE_REGISTRY = {}
_TYPES = {
    "int": int,
    "str": str,
    "bool": bool,
    "float": float,
    "list": list,
    "dict": dict,
}


class Property(object):
    @classmethod
    def deserialise(cls, data):
        # type: (dict) -> Property
        return cls(
            data["name"],
            _TYPES[data["type"]],
            data["default"],
            choices=data["choices"],
        )

    def __init__(self, name, type_, default, choices=None):
        # type: (str, type, object, list) -> None
        self._name = name
        self._type = type_
        self._default = default
        self._choices = choices
        self._value = default

    def __repr__(self):
        return "{}({!r}, {!r}, {!r}, choices={!r})".format(
            self.__class__.__name__,
            self._name,
            self._type,
            self._default,
            self._choices,
        )

    @property
    def choices(self):
        # type: () -> list
        return self._choices

    @property
    def default(self):
        # type: () -> object
        return self._default

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def type(self):
        # type: () -> type
        return self._type

    @property
    def value(self):
        # type: () -> object
        return self._value

    @value.setter
    def value(self, value):
        # type: (object) -> None
        self._value = value

    def serialise(self):
        # type: () -> dict
        return {
            "name": self._name,
            "type": self._type.__name__,
            "default": self._default,
            "choices": self._choices,
            "value": self._value,
        }


class GroupProperty(object):
    @classmethod
    def deserialise(cls, data):
        # type: (dict) -> GroupProperty
        prop = cls(data["name"])
        for prop_data in data["properties"]:
            if "properties" in prop_data:
                child = GroupProperty.deserialise(prop_data)
            else:
                child = Property.deserialise(prop_data)
            prop.add_property(child)
        return prop

    def __init__(self, name):
        # type: (str) -> None
        self._name = name
        self._properties = {}

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self._name)

    def __getitem__(self, item):
        return self._properties[item]

    def __setitem__(self, key, value):
        self._properties[key].value = value

    def __bool__(self):
        return bool(self._properties)

    @property
    def name(self):
        # type: () -> str
        return self._name

    def add_property(self, prop):
        # type: (Property|GroupProperty) -> None
        if prop.name in self._properties:
            raise ValueError("Property already exists: {}".format(prop.name))
        self._properties[prop.name] = prop

    def serialise(self):
        # type: () -> dict
        return {
            "name": self._name,
            "properties": [p.serialise() for p in self._properties.values()],
        }


class Port(object):
    Input = 0
    Output = 1

    def __init__(self, node, name, direction):
        # type: (Node, str, int) -> None
        self._node = node
        self._name = name
        self._direction = direction
        self._connected = []

    def __repr__(self):
        return "{}({!r}, {!r}, {})".format(
            self.__class__.__name__, self._node, self._name, self._direction
        )

    def __str__(self):
        return "{}.{}".format(self._node, self._name)

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
        elif port.direction == self._direction:
            raise ValueError("Cannot connect ports of the same direction")
        elif port.node == self.node:
            raise ValueError("Cannot connect a node's port to it's own node")
        elif port.node.parent() != self.node.parent():
            raise ValueError("Cannot connect ports under different parents")
        else:
            self._connected.append(port)
            port._connected.append(self)

    def connected(self, index):
        # type: (int) -> Port
        return self._connected[index]

    def disconnect(self, port):
        # type: (Port) -> None
        self._connected.remove(port)
        port._connected.remove(self)

    def isolate(self):
        for port in reversed(self._connected):
            self.disconnect(port)

    def iter_connected(self):
        # type: () -> types.Iterator[Port]
        for port in self._connected:
            yield port

    def num_connected(self):
        # type: () -> int
        return len(self._connected)


class Node(object):
    @classmethod
    def deserialise(cls, data):
        # type: (dict) -> Node
        node = cls(data["name"])

        properties = data["properties"]
        if properties:
            node._properties = GroupProperty.deserialise(properties)

        for input_name in data["inputs"]:
            node.add_input(input_name)

        for output_name in data["outputs"]:
            node.add_output(output_name)

        return node

    def __init__(self, name):
        # type: (str) -> None
        self._name = name
        self._properties = GroupProperty("properties")

        self._inputs = []
        self._outputs = []
        self._parent = None

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self._name)

    def __str__(self):
        names = []
        node = self
        while node:
            names.append(node.name)
            node = node._parent
        return ".".join(reversed(names))

    def __getitem__(self, item):
        return self._properties[item]

    def __setitem__(self, key, value):
        self._properties[key].set(value)

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def properties(self):
        # type: () -> GroupProperty
        return self._properties

    def add_input(self, name):
        # type: (str) -> Port
        port = Port(self, name, Port.Input)
        self._inputs.append(port)
        return port

    def add_output(self, name):
        # type: (str) -> Port
        port = Port(self, name, Port.Output)
        self._outputs.append(port)
        return port

    def input(self, name_or_index):
        # type: (int|str) -> Port
        return self._item(self._inputs, name_or_index)

    def isolate(self):
        for port in self._inputs + self._outputs:
            port.isolate()

    def iter_inputs(self):
        # type: () -> types.Iterator[Port]
        for i in self._inputs:
            yield i

    def iter_outputs(self):
        # type: () -> types.Iterator[Port]
        for o in self._outputs:
            yield o

    def num_inputs(self):
        # type: () -> int
        return len(self._inputs)

    def num_outputs(self):
        # type: () -> int
        return len(self._outputs)

    def output(self, name_or_index):
        # type: (int|str) -> Port
        return self._item(self._outputs, name_or_index)

    def parent(self):
        # type: () -> Node
        return self._parent

    def remove_input(self, port):
        # type: (Port) -> None
        if port not in self._inputs:
            raise ValueError(
                "Port {!r} not in inputs for node: {}".format(port.name, self)
            )
        port.isolate()
        self._inputs.remove(port)

    def remove_output(self, port):
        # type: (Port) -> None
        if port not in self._outputs:
            raise ValueError(
                "Port {!r} not in outputs for node: {}".format(port.name, self)
            )
        port.isolate()
        self._outputs.remove(port)

    def serialise(self):
        # type: () -> dict
        return {
            "name": self._name,
            "type": self.type(),
            "properties": (
                self._properties.serialise() if self._properties else None
            ),
            "inputs": [p.name for p in self._inputs],
            "outputs": [p.name for p in self._outputs],
        }

    def type(self):
        # type: () -> str
        return self.__class__.__name__

    @staticmethod
    def _item(lst, name_or_index):
        # type: (list[Port], str|int) -> Port
        if isinstance(name_or_index, int):
            return lst[name_or_index]
        else:
            for o in lst:
                if o.name == name_or_index:
                    return o
        raise ValueError("Unknown port: {}".format(name_or_index))


class Group(Node):
    @classmethod
    def deserialise(cls, data):
        # type: (dict) -> Group
        group_node = super(Group, cls).deserialise(data)  # type: Group
        for child_data in data["children"]:
            node_class = get_registered_node_type(child_data["type"])
            child = node_class.deserialise(child_data)
            group_node.add_node(child)

        for source_node, source_port, target_node, target_port in data["connections"]:
            i = group_node.child(source_node).input(source_port)
            o = group_node.child(target_node).output(target_port)
            i.connect(o)

        return group_node

    def __init__(self, name):
        # type: (str) -> None
        super(Group, self).__init__(name)
        self._children = {}

    def add_node(self, node):
        # type: (Node) -> None
        # If the parents are the same then nothing is changing and can be
        # ignored, unless both parents are None in which case it's a new node
        # being added to a root graph
        if node.parent() == self.parent() and node.parent() is not None:
            return
        if node == self:
            raise ValueError("Cannot add a node as it's own child")
        if node.name in self._children:
            raise ValueError("Node name already exists as child: {}".format(node.name))
        # Port's can only be connected under the same parent so must be
        # disconnected if switching
        node.isolate()
        self._children[node.name] = node
        node._parent = self

    def child(self, name):
        # type: (str) -> Node|Group
        return self._children[name]

    def iter_children(self):
        # type: () -> types.Iterator[Node|Group]
        for c in self._children.values():
            yield c

    def num_children(self):
        # type: () -> int
        return len(self._children)

    def remove_node(self, node):
        # type: (Node) -> None
        self._children.pop(node.name)
        node.isolate()
        node._parent = None

    def serialise(self):
        # type: () -> dict
        data = super(Group, self).serialise()
        data["children"] = [n.serialise() for n in self._children.values()]
        data["connections"] = [
            [node.name, port.name, connected.node.name, connected.name]
            for node in self._children.values()
            for port in node.iter_inputs()
            for connected in port.iter_connected()
        ]
        return data


class Graph(Group):
    @classmethod
    def deserialise(cls, data):
        # type: (dict) -> Graph
        graph = super(Graph, cls).deserialise(data)  # type: Graph
        graph.rebuild_nodes()
        return graph

    @classmethod
    def load(cls, filepath):
        # type: (str) -> Graph
        with open(filepath, "r") as stream:
            data = json.load(stream)

        return cls.deserialise(data)

    def __init__(self, name="Graph"):
        # type: (str) -> None
        super(Graph, self).__init__(name)
        self._nodes = {}

    def create_node(self, node_type, name, parent=None):
        # type: (str, str, Node) -> Node
        node_class = get_registered_node_type(node_type)

        # Scan for existing names and increment the number
        num = -1
        pattern = "^{}(\d+)?$".format(name)
        for node_name in self._nodes:
            match = re.match(pattern, node_name)
            if match:
                num = max(num, int(match.group(1) or 0))

        if num > -1:
            name = "{}{}".format(name, num + 1)

        node = node_class(name)
        parent_node = parent or self
        parent_node.add_node(node)
        self._nodes[name] = node
        return node

    def delete_node(self, node):
        if node.name not in self._nodes:
            raise ValueError("Node {} is not part of {}".format(node, self))
        node.parent().remove_node(node)
        self._nodes.pop(node.name)

    def get_node(self, name):
        # type: (str) -> Node
        return self._nodes[name]

    def rebuild_nodes(self):
        self._nodes.clear()
        self._rebuild(self)

    def save(self, filepath):
        # type: (str) -> None
        data = self.serialise()
        with open(filepath, "w") as stream:
            json.dump(data, stream)

    def _rebuild(self, node):
        # type: (Group) -> None
        for child in node.iter_children():
            self._nodes[child.name] = child
            if isinstance(child, Group):
                self._rebuild(child)


def get_registered_node_type(node_type):
    # type: (str) -> types.Type[Node]
    return _NODE_TYPE_REGISTRY[node_type]


# One downside of this system is that it's unknown where nodes are being
# registered from (unless logged, but then it's still not easy to check). An
# environment variable with paths to load node types from is far clearer.
def register_node_type(node_type, node_class):
    # type: (str, types.Type[Node]) -> None
    if node_type in _NODE_TYPE_REGISTRY:
        raise ValueError("Node type already registered: {}".format(node_type))
    if Node not in node_class.mro():
        raise TypeError("Node class must inherit from Node")
    _NODE_TYPE_REGISTRY[node_type] = node_class


register_node_type("Node", Node)
register_node_type("Group", Group)
register_node_type("Graph", Graph)


if __name__ == '__main__':
    class MyNode(Node):
        def __init__(self, name):
            super(MyNode, self).__init__(name)
            self.properties.add_property(Property("two", str, ""))
            self.properties.add_property(Property("three", int, 0))
            prop2 = GroupProperty("four")
            prop2.add_property(Property("five", bool, True))
            self.properties.add_property(prop2)

    register_node_type("MyNode", MyNode)

    def ascii_tree(node, level=0):
        lines = [". " * level + repr(node)]
        if isinstance(node, Group):
            for child in node.iter_children():
                lines.extend(ascii_tree(child, level=level+1))
        return lines

    def print_tree(node):
        print("\n".join(ascii_tree(node)))

    # g = Graph.load(r"C:\Users\Matthew\Documents\temp\qt_utils\scene.json")
    # print_tree(g)
    g = Graph("Graph")
    node = g.create_node("MyNode", "name")
    group = g.create_node("Group", "name")
    group.add_input("one")
    child1 = g.create_node("Node", "name", parent=group)
    child2 = g.create_node("Node", "name", parent=group)
    print(list(g.iter_children()))
    i = child1.add_output("out1")
    o = child2.add_input("in1")
    i.connect(o)
    print("Node:", node["two"])
    print("Node:", node["two"])
    print("Node:", node["three"])
    print("Node:", node["four"]["five"])
    print(node)
    print(group)
    print(child1)
    print(child2)
    print(g.child("name1").child("name2").output("out1"))
    print(g.child("name1").child("name3").input("in1"))
    print(list(g.child("name1").child("name3").input("in1").iter_connected()))
    print(list(g.child("name1").child("name2").output("out1").iter_connected()))
    # g.child("name1").child("name3").input("in1").isolate()
    # print(list(g.child("name1").child("name3").input("in1").iter_connected()))
    # print(list(g.child("name1").child("name2").output("out1").iter_connected()))
    print(g.get_node("name3"))
    g.save(r"C:\Users\Matthew\Documents\temp\qt_utils\scene.json")
