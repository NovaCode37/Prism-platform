from modules.graph_builder import (
    _node,
    _edge,
    _shape,
    build_graph
)
class TestGraphBuilderNode:
    def test_node(self):
        result = _node("1","test","target","testTitle")
        assert result == {"id":"1","label":"test","full_label":"test",
                        "type":"target","color":"#00d4ff","title":"testTitle","shape":"star"}
    def test_node_with_no_title(self):
        result = _node("1","test","target")
        assert result == {"id":"1","label":"test","full_label":"test",
                        "type":"target","color":"#00d4ff","title":"test","shape":"star"}
    def test_node_with_very_long_lable(self):
        result = _node("1",,"target")
    def test_node_with_no_type(self):
