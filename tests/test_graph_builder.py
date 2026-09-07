# tests/test_graph_builder.py
import pytest
from modules.graph_builder import build_graph, NODE_COLORS

class TestGraphBuilder:
    def test_target_node_always_present(self):
        """The target node should always be present in the graph."""
        graph = build_graph("example.com", "domain", {})
        
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) >= 1
        
        target_nodes = [n for n in graph["nodes"] if n["type"] == "target"]
        assert len(target_nodes) == 1
        assert target_nodes[0]["full_label"] == "example.com"
        assert target_nodes[0]["color"] == "#00d4ff"
        assert target_nodes[0]["shape"] == "star"

    def test_whois_nodes_and_edges(self):
        """WHOIS data should create organization, email, and nameserver nodes."""
        results = {
            "whois": {
                "org": "Test Corp",
                "emails": ["admin@test.com", "abuse@test.com"],
                "name_servers": ["ns1.test.com", "ns2.test.com"],
                "error": None,
            }
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "org::Test Corp" in node_ids
        assert "email::admin@test.com" in node_ids
        assert "email::abuse@test.com" in node_ids
        assert "domain::ns1.test.com" in node_ids
        assert "domain::ns2.test.com" in node_ids
        
        # Check edges
        edge_sources = [e["from"] for e in graph["edges"]]
        edge_targets = [e["to"] for e in graph["edges"]]
        
        assert "target::test.com" in edge_sources
        assert "org::Test Corp" in edge_targets
        assert "email::admin@test.com" in edge_targets
        assert "email::abuse@test.com" in edge_targets

    def test_geoip_nodes_and_edges(self):
        """GeoIP data should create IP and organization nodes."""
        results = {
            "geoip": {
                "ip": "93.184.216.34",
                "city": "Norwell",
                "country": "US",
                "org": "AS15133 Edgecast Inc.",
                "error": None,
            }
        }
        
        graph = build_graph("example.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "ip::93.184.216.34" in node_ids
        assert "org::AS15133 Edgecast Inc." in node_ids
        
        # IP node should have correct attributes
        ip_node = next(n for n in graph["nodes"] if n["id"] == "ip::93.184.216.34")
        assert ip_node["type"] == "ip"
        assert ip_node["color"] == "#fd79a8"
        assert ip_node["shape"] == "diamond"
        assert "Norwell" in ip_node["title"]

    def test_cert_transparency_subdomain_nodes(self):
        """Certificate transparency data should create subdomain nodes."""
        results = {
            "cert_transparency": {
                "subdomains": ["api.test.com", "mail.test.com", "www.test.com"],
                "total_certs": 10,
                "error": None,
            }
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "subdomain::api.test.com" in node_ids
        assert "subdomain::mail.test.com" in node_ids
        assert "subdomain::www.test.com" in node_ids
        
        # Subdomain should have correct attributes
        sub_node = next(n for n in graph["nodes"] if n["id"] == "subdomain::api.test.com")
        assert sub_node["type"] == "subdomain"
        assert sub_node["color"] == "#74b9ff"
        assert sub_node["shape"] == "box"

    def test_blackbird_account_nodes(self):
        """Blackbird results should create account nodes for found accounts only."""
        results = {
            "blackbird": [
                {"site": "GitHub", "url": "https://github.com/test", "status": "found"},
                {"site": "Twitter", "url": "https://x.com/test", "status": "found"},
                {"site": "Reddit", "url": "https://reddit.com/user/test", "status": "not_found"},
            ]
        }
        
        graph = build_graph("test", "username", results)
        account_nodes = [n for n in graph["nodes"] if n["type"] == "account"]
        
        # Only found accounts should be added
        assert len(account_nodes) == 2
        account_sites = [n["id"] for n in account_nodes]
        assert "account::GitHub" in account_sites
        assert "account::Twitter" in account_sites
        
        # Check edges from target to accounts
        edges_from_target = [e for e in graph["edges"] if e["from"] == "target::test"]
        assert len(edges_from_target) == 2
        assert all(e["label"] == "profile" for e in edges_from_target)

    def test_hunter_email_nodes(self):
        """Hunter.io email data should create email nodes."""
        results = {
            "hunter": {
                "emails": ["user1@test.com", "user2@test.com", "user3@test.com"],
                "error": None,
            }
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "email::user1@test.com" in node_ids
        assert "email::user2@test.com" in node_ids
        assert "email::user3@test.com" in node_ids

    def test_shodan_vulnerability_nodes(self):
        """Shodan vulnerabilities should create vulnerability nodes."""
        results = {
            "shodan": {
                "ip": "45.33.32.156",
                "open_ports": [22, 80],
                "vulns": ["CVE-2021-44228", "CVE-2022-0778"],
                "error": None,
            }
        }
        
        graph = build_graph("45.33.32.156", "ip", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "vuln::CVE-2021-44228" in node_ids
        assert "vuln::CVE-2022-0778" in node_ids
        
        # Vulnerability nodes should have correct attributes
        vuln_node = next(n for n in graph["nodes"] if n["id"] == "vuln::CVE-2021-44228")
        assert vuln_node["type"] == "vulnerability"
        assert vuln_node["color"] == "#d63031"
        assert vuln_node["shape"] == "triangleDown"

    def test_website_technology_and_social_nodes(self):
        """Website analysis should create technology and account nodes."""
        results = {
            "website": {
                "url": "https://test.com",
                "technologies": ["nginx", "WordPress", "jQuery"],
                "emails": ["contact@test.com"],
                "social_links": [
                    {"platform": "twitter", "username": "testco"},
                    {"platform": "linkedin", "username": "test-corp"},
                ],
                "error": None,
            }
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "tech::nginx" in node_ids
        assert "tech::WordPress" in node_ids
        assert "tech::jQuery" in node_ids
        assert "email::contact@test.com" in node_ids
        assert "account::twitter/@testco" in node_ids
        assert "account::linkedin/@test-corp" in node_ids

    def test_breach_nodes(self):
        """Breach data should create vulnerability nodes."""
        results = {
            "breaches": {
                "breaches": ["Adobe", "LinkedIn", "MySpace"],
                "error": None,
            }
        }
        
        graph = build_graph("test@example.com", "email", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        assert "breach::Adobe" in node_ids
        assert "breach::LinkedIn" in node_ids
        assert "breach::MySpace" in node_ids
        
        # Breach nodes should be vulnerability type
        breach_node = next(n for n in graph["nodes"] if n["id"] == "breach::Adobe")
        assert breach_node["type"] == "vulnerability"
        assert breach_node["color"] == "#d63031"

    def test_node_ids_are_unique(self):
        """All node IDs should be unique."""
        results = {
            "whois": {
                "org": "Test Corp",
                "emails": ["admin@test.com"],
                "name_servers": ["ns1.test.com"],
                "error": None,
            },
            "geoip": {
                "ip": "93.184.216.34",
                "org": "Test Corp",  # Same org as WHOIS
                "error": None,
            },
            "cert_transparency": {
                "subdomains": ["www.test.com", "api.test.com"],
                "error": None,
            },
            "website": {
                "technologies": ["nginx"],
                "social_links": [{"platform": "twitter", "username": "test"}],
                "emails": ["contact@test.com"],
                "error": None,
            },
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        # All IDs should be unique
        assert len(node_ids) == len(set(node_ids))
        
        # Same organization from WHOIS and GeoIP should be deduplicated
        org_count = sum(1 for n in graph["nodes"] if n["id"] == "org::Test Corp")
        assert org_count == 1

    def test_label_truncation(self):
        """Labels should be truncated to 30 characters."""
        results = {
            "whois": {
                "org": "This Is A Very Long Organization Name That Exceeds 30 Characters",
                "error": None,
            }
        }
        
        graph = build_graph("test.com", "domain", results)
        org_node = next(n for n in graph["nodes"] if n["type"] == "organization")
        
        assert len(org_node["label"]) <= 30
        assert org_node["label"].endswith("...")
        assert org_node["full_label"] == "This Is A Very Long Organization Name That Exceeds 30 Characters"

    def test_error_results_are_skipped(self):
        """Modules with errors should not create nodes."""
        results = {
            "whois": {
                "error": "Domain not found",
            },
            "geoip": {
                "error": "IP not found",
            },
            "cert_transparency": {
                "error": "Timeout",
            },
        }
        
        graph = build_graph("test.com", "domain", results)
        node_ids = [n["id"] for n in graph["nodes"]]
        
        # Only the target node should exist
        assert len(graph["nodes"]) == 1
        assert "target::test.com" in node_ids

    def test_empty_results(self):
        """Empty results should only create the target node."""
        graph = build_graph("test.com", "domain", {})
        
        assert len(graph["nodes"]) == 1
        assert graph["nodes"][0]["type"] == "target"
        assert graph["nodes"][0]["id"] == "target::test.com"
        assert graph["edges"] == []

    def test_different_scan_types(self):
        """Graph should work for all scan types."""
        for scan_type in ["domain", "ip", "email", "phone", "username"]:
            graph = build_graph("target", scan_type, {})
            assert graph["nodes"][0]["type"] == "target"
            # Should not raise any errors

    def test_edges_have_required_fields(self):
        """All edges should have required fields."""
        results = {
            "whois": {
                "org": "Test Corp",
                "emails": ["admin@test.com"],
                "name_servers": ["ns1.test.com"],
                "error": None,
            },
        }
        
        graph = build_graph("test.com", "domain", results)
        
        for edge in graph["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert "label" in edge
            assert "dashes" in edge
            assert "color" in edge
            assert "smooth" in edge

    def test_nodes_have_required_fields(self):
        """All nodes should have required fields."""
        graph = build_graph("test.com", "domain", {})
        
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "full_label" in node
            assert "type" in node
            assert "color" in node
            assert "title" in node
            assert "shape" in node

    def test_duplicate_nodes_from_different_sources(self):
        """The same IP/domain from different sources should be deduplicated."""
        results = {
            "geoip": {
                "ip": "93.184.216.34",
                "error": None,
            },
            "shodan": {
                "ip": "93.184.216.34",
                "open_ports": [80, 443],
                "error": None,
            },
        }
        
        graph = build_graph("example.com", "domain", results)
        ip_count = sum(1 for n in graph["nodes"] if n["id"] == "ip::93.184.216.34")
        assert ip_count == 1

    def test_all_node_colors_are_defined(self):
        """All node types should have colors defined in NODE_COLORS."""
        results = {
            "whois": {
                "org": "Test Corp",
                "emails": ["admin@test.com"],
                "name_servers": ["ns1.test.com"],
                "error": None,
            },
            "geoip": {
                "ip": "93.184.216.34",
                "org": "Test Corp",
                "error": None,
            },
            "cert_transparency": {
                "subdomains": ["www.test.com"],
                "error": None,
            },
            "website": {
                "technologies": ["nginx"],
                "social_links": [{"platform": "twitter", "username": "test"}],
                "emails": ["contact@test.com"],
                "error": None,
            },
            "shodan": {
                "vulns": ["CVE-2021-44228"],
                "error": None,
            },
            "breaches": {
                "breaches": ["Adobe"],
                "error": None,
            },
        }
        
        graph = build_graph("test.com", "domain", results)
        
        node_types = set(n["type"] for n in graph["nodes"])
        for node_type in node_types:
            # All node types should be in NODE_COLORS (except maybe some edge cases)
            if node_type != "target":  # target is always defined
                assert node_type in NODE_COLORS or node_type == "url", \
                    f"Node type '{node_type}' not in NODE_COLORS"