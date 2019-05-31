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
        self._connected.append(port)
        port._connected.append(self)

    def get_connected_by_index(self, index):
        # type: (int) -> Port
        return self._connected[index]


class Node(object):
    def __init__(self, name):
        # type: (str) -> None
        self._name = name
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
        return [port.name for port in self._inputs]

    def list_outputs(self):
        # type: () -> list[str]
        return [port.name for port in self._outputs]

    def remove_input_port(self, port):
        # type: (Port) -> None
        self._inputs.remove(port)

    def remove_output_port(self, port):
        # type: (Port) -> None
        self._outputs.remove(port)


if __name__ == '__main__':
    n1 = Node("one")
    n1.add_input_port("i1")
    n1.add_input_port("i2")
    n1.add_output_port("o1")

    n2 = Node("two")
    n2.add_input_port("i1")
    n2.add_output_port("o1")

    p1 = n1.get_output_by_index(0)
    p2 = n2.get_input_by_name("i1")
    p1.connect(p2)

    print(n1)
    print(p1)
    print(p2)
    print(n2)
