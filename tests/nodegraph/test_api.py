from qt_utils.nodegraph import api


def test_node():
    node = api.Node("Node", "node")
    assert node.name == "node"
    assert node.get_output_count() == 0
    assert node.get_input_count() == 0
    assert node.type() == "Node"

    p = node.add_input_port("in_1")
    assert isinstance(p, api.Port)
    assert node.get_input_by_name("in_1") == p
    assert node.get_input_by_index(0) == p
    assert node.list_inputs() == [p]
    node.remove_input_port(p)
    assert node.get_input_count() == 0

    p = node.add_output_port("out_1")
    assert isinstance(p, api.Port)
    assert node.get_output_by_name("out_1") == p
    assert node.get_output_by_index(0) == p
    assert node.list_outputs() == [p]
    node.remove_output_port(p)
    assert node.get_output_count() == 0


def test_port():
    node1 = api.Node("Node1", "node")
    port1 = api.Port(node1, "port1")
    assert port1.name == "port1"
    assert port1.node == node1

    node2 = api.Node("Node2", "node")
    port2 = api.Port(node2, "port1")

    port1.connect(port2)
    assert port1.get_connection_count() == 1
    assert port2.get_connection_count() == 1
    assert port1.get_connected_by_index(0) == port2
    assert port2.get_connected_by_index(0) == port1
