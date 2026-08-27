from modules.graph_export import (
    _hex_to_rgb,
    to_graphml,
    to_gexf
)
import xml.etree.ElementTree as ET
import pytest
import copy

@pytest.fixture
def graph():
    return {
        "nodes": [
            {
                "id": "1",
                "label": "Node A",
                "type": "function",
                "color": "#FF0000",
            },
            {
                "id": "2",
                "label": "Node B",
                "type": "class",
                "color": "#00FF00",
            },
        ],
        "edges": [
            {
                "from": "1",
                "to": "2",
                "label": "calls",
            }
        ],
    }

class TestHexToRgb:
    def test_hex_to_rgb_with_non_string_input(self):
        assert _hex_to_rgb(123) == (150,150,150)
        assert _hex_to_rgb('A') == (150,150,150)
        assert _hex_to_rgb([1,2,3]) == (150,150,150)
        assert _hex_to_rgb({1:2}) == (150,150,150)
        assert _hex_to_rgb(True) == (150,150,150)
    def test_hex_to_rgb_with_wrong_hex_value(self):
        assert _hex_to_rgb("#000ffff") == (150,150,150)
        assert _hex_to_rgb("#zzzzzz") == (150,150,150)
    def test_hex_to_rgb_with_right_value(self):
        assert _hex_to_rgb("#000000") == (0,0,0)

class TestGraphml:
    def test_to_graphml_empty_graph(self):
        result = to_graphml({})

        root = ET.fromstring(result)

        ns = "http://graphml.graphdrawing.org/xmlns"

        assert root.tag == f"{{{ns}}}graphml"

        graph = root.find(f"{{{ns}}}graph")
        assert graph is not None
        assert graph.get("edgedefault") == "directed"

        nodes = graph.findall(f"{{{ns}}}node")
        edges = graph.findall(f"{{{ns}}}edge")

        assert nodes == []
        assert edges == []

        keys = root.findall(f"{{{ns}}}key")

        assert len(keys) == 4

        key_data = {
            key.get("id"): {
                "for": key.get("for"),
                "attr.name": key.get("attr.name"),
                "attr.type": key.get("attr.type"),
            }
            for key in keys
        }

        assert key_data == {
            "label": {
                "for": "node",
                "attr.name": "label",
                "attr.type": "string",
            },
            "type": {
                "for": "node",
                "attr.name": "type",
                "attr.type": "string",
            },
            "color": {
                "for": "node",
                "attr.name": "color",
                "attr.type": "string",
            },
            "elabel": {
                "for": "edge",
                "attr.name": "label",
                "attr.type": "string",
            },
        }
    def test_to_graphml_graph(self,graph):
        result = to_graphml(graph)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert '<node id="1">' in result
        assert '<node id="2">' in result
        assert "Node A" in result
        assert "Node B" in result
    def test_to_graphml_graph_with_no_label(self,graph):
        test_graph = copy.deepcopy(graph)
        for node in test_graph["nodes"]:
            node.pop("label")
        result = to_graphml(test_graph)
        root = ET.fromstring(result)

        node = root.find(".//{http://graphml.graphdrawing.org/xmlns}node")
        assert node is not None
        assert node.get("id") == "1"

        data = {
            element.get("key"): element.text
            for element in node
        }

        assert data["label"] in (None, "")
        assert data["type"] == "function"
        assert data["color"] == "#FF0000"
    def test_to_graphml_node_without_type_or_color(self,graph):
        test_graph = copy.deepcopy(graph)
        for node in test_graph["nodes"]:
            node.pop("type")
            node.pop("color")
        result = to_graphml(test_graph)

        root = ET.fromstring(result)

        node = root.find(".//{http://graphml.graphdrawing.org/xmlns}node")
        assert node is not None

        data = {
            element.get("key"): element.text
            for element in node
        }
        
        assert data["type"] in (None, "")
        assert data["color"] in (None, "")
class TestGexf:
    def test_to_gexf_empty_graph(self):
        result = to_gexf({})

        root = ET.fromstring(result)

        ns = "http://gexf.net/1.3"

        assert root.tag == f"{{{ns}}}gexf"

        graph = root.find(f"{{{ns}}}graph")
        assert graph is not None
        assert graph.get("mode") == "static"
        assert graph.get("defaultedgetype") == "directed"

        nodes = graph.find(f"{{{ns}}}nodes")
        edges = graph.find(f"{{{ns}}}edges")

        assert nodes is not None
        assert edges is not None
        assert list(nodes) == []
        assert list(edges) == []
    def test_to_gexf_graph(self,graph):
        result = to_gexf(graph)
        root = ET.fromstring(result)

        ns = "http://gexf.net/1.3"

        graph_el = root.find(f"{{{ns}}}graph")
        assert graph_el is not None

        nodes = graph_el.find(f"{{{ns}}}nodes")
        edges = graph_el.find(f"{{{ns}}}edges")

        assert nodes is not None
        assert edges is not None

        assert len(nodes) == 2
        assert len(edges) == 1
    def test_to_gexf_color(self,graph):
        result = to_gexf(graph)
        root = ET.fromstring(result)

        ns = "http://gexf.net/1.3"

        node = root.find(f".//{{{ns}}}node")
        assert node is not None

        color = node.find("{http://gexf.net/1.3/viz}color")
        assert color is not None

        assert color.get("r") == "255"
        assert color.get("g") == "0"
        assert color.get("b") == "0"