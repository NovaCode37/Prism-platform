import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple


def _hex_to_rgb(color: Any) -> Tuple[int, int, int]:
    if not isinstance(color, str):
        return (150, 150, 150)
    c = color.strip().lstrip("#")
    if len(c) != 6:
        return (150, 150, 150)
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except ValueError:
        return (150, 150, 150)


def _nodes_edges(graph: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    return nodes, edges


def to_graphml(graph: Dict[str, Any]) -> str:
    ns = "http://graphml.graphdrawing.org/xmlns"
    root = ET.Element("graphml", {"xmlns": ns})

    for key_id, target, name in (
        ("label", "node", "label"),
        ("type", "node", "type"),
        ("color", "node", "color"),
        ("elabel", "edge", "label"),
    ):
        ET.SubElement(root, "key", {
            "id": key_id, "for": target, "attr.name": name, "attr.type": "string",
        })

    g = ET.SubElement(root, "graph", {"edgedefault": "directed"})

    nodes, edges = _nodes_edges(graph)
    for n in nodes:
        node_el = ET.SubElement(g, "node", {"id": str(n.get("id", ""))})
        for key_id, value in (
            ("label", n.get("full_label") or n.get("label") or ""),
            ("type", n.get("type") or ""),
            ("color", n.get("color") or ""),
        ):
            data = ET.SubElement(node_el, "data", {"key": key_id})
            data.text = str(value)

    for i, e in enumerate(edges):
        edge_el = ET.SubElement(g, "edge", {
            "id": f"e{i}",
            "source": str(e.get("from", "")),
            "target": str(e.get("to", "")),
        })
        if e.get("label"):
            data = ET.SubElement(edge_el, "data", {"key": "elabel"})
            data.text = str(e["label"])

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def to_gexf(graph: Dict[str, Any]) -> str:
    root = ET.Element("gexf", {
        "xmlns": "http://gexf.net/1.3",
        "xmlns:viz": "http://gexf.net/1.3/viz",
        "version": "1.3",
    })
    g = ET.SubElement(root, "graph", {"mode": "static", "defaultedgetype": "directed"})

    attrs = ET.SubElement(g, "attributes", {"class": "node"})
    ET.SubElement(attrs, "attribute", {"id": "0", "title": "type", "type": "string"})

    nodes, edges = _nodes_edges(graph)

    nodes_el = ET.SubElement(g, "nodes")
    for n in nodes:
        node_el = ET.SubElement(nodes_el, "node", {
            "id": str(n.get("id", "")),
            "label": str(n.get("full_label") or n.get("label") or ""),
        })
        values = ET.SubElement(node_el, "attvalues")
        ET.SubElement(values, "attvalue", {"for": "0", "value": str(n.get("type") or "")})
        r, gr, b = _hex_to_rgb(n.get("color"))
        ET.SubElement(node_el, "viz:color", {"r": str(r), "g": str(gr), "b": str(b)})

    edges_el = ET.SubElement(g, "edges")
    for i, e in enumerate(edges):
        attrib = {
            "id": str(i),
            "source": str(e.get("from", "")),
            "target": str(e.get("to", "")),
        }
        if e.get("label"):
            attrib["label"] = str(e["label"])
        ET.SubElement(edges_el, "edge", attrib)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
