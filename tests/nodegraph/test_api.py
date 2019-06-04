import pytest

from qt_utils.nodegraph import api


def test_node():
    node = api.Node("Node", "node", "0")
    assert node.name == "node"
    assert node.get_output_count() == 0
    assert node.get_input_count() == 0
    assert node.type() == "Node"
    assert node.identifier == "0"

    data = node.serialize()
    assert api.Node.deserialize(data) == node

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
    node1 = api.Node("Node1", "node", "0")
    port1 = api.Port(node1, "port1", api.Port.Input)
    assert port1.name == "port1"
    assert port1.node == node1
    assert port1.direction == api.Port.Input

    node2 = api.Node("Node2", "node", "1")
    port2 = api.Port(node2, "port1", api.Port.Output)
    assert port2.direction == api.Port.Output

    port1.connect(port2)
    assert port1.get_connection_count() == 1
    assert port2.get_connection_count() == 1
    assert port1.get_connected_by_index(0) == port2
    assert port2.get_connected_by_index(0) == port1


def test_scene():
    scene = api.Scene()
    node1 = scene.create_node("Node", "node")
    assert node1.name == "node"
    assert scene.get_node_by_name("node") == node1

    node2 = scene.create_node("Node", "node")
    assert node2.name == "node1"
    assert scene.get_node_by_name("node1") == node2

    assert node2.identifier != node1.identifier

    assert set(scene.list_nodes()) == {node1, node2}

    with pytest.raises(api.NodeError):
        scene.create_node("Node", "node", identifier=node2.identifier)

    with pytest.raises(api.NodeError):
        scene.create_node("Node", "node", identifier=0)
