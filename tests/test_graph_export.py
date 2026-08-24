from modules.graph_export import (
    _hex_to_rgb,
    to_graphml,
    to_gexf
)
import xml.etree.ElementTree as ET
class TestHexToRgb:
    def test_hex_to_rgb_with_non_string_input(self):
        assert _hex_to_rgb(123) == (150,150,150)
        assert _hex_to_rgb('A') == (150,150,150)
        assert _hex_to_rgb([1,2,3]) == (150,150,150)
        assert _hex_to_rgb({1:2}) == (150,150,150)
        assert _hex_to_rgb(True) == (150,150,150)
    def test_hex_to_rgb_with_wrong_hex_value(self):
        assert _hex_to_rgb("123abc") == (150,150,150)
        assert _hex_to_rgb("#000ffff") == (150,150,150)
        assert _hex_to_rgb("#zzzzzz") == (150,150,150)
    def test_hex_to_rgb_with_right_value(self):
        assert _hex_to_rgb("#000000") == (0,0,0)
class TestGraphml:
    def test_to_graphml_empyt_graph(self):
        ns = "http://graphml.graphdrawing.org/xmlns"
        root = ET.Element("graphml", {"xmlns": ns})
        g = ET.SubElement(root, "graph", {"edgedefault": "directed"})
        assert to_graphml({}) == '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    def test_to_graphml_graph(self):
        graph = {
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
        result = to_graphml(graph)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert '<node id="1">' in result
        assert '<node id="2">' in result
        assert "Node A" in result
        assert "Node B" in result
    def test_to_graphml_graph_with_no_label(self):
        graph = {
            "nodes": [
                {
                    "id": "1",
                    "type": "function",
                    "color": "#FF0000",
                }
            ],
            "edges": [],
        }
        result = to_graphml(graph)
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
    def test_to_graphml_node_without_type_or_color():
        graph = {
            "nodes": [
                {
                    "id": "1",
                }
            ],
            "edges": [],
        }

        result = to_graphml(graph)

        root = ET.fromstring(result)

        node = root.find(".//{http://graphml.graphdrawing.org/xmlns}node")
        assert node is not None

        data = {
            element.get("key"): element.text
            for element in node
        }

        assert data["label"] in (None, "")
        assert data["type"] in (None, "")
        assert data["color"] in (None, "")
# class TestGexf:
