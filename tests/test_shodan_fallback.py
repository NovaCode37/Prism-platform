import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.shodan_lookup import ShodanLookup

INTERNETDB_PAYLOAD = {
    "ip": "45.33.32.156",
    "ports": [80, 22, 31337, 123],
    "hostnames": ["scanme.nmap.org"],
    "tags": ["cloud"],
    "vulns": ["CVE-2021-44224", "CVE-2019-0220"],
    "cpes": ["cpe:/a:apache:http_server"],
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", raise_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


def _lookup(key=""):
    sh = ShodanLookup()
    sh.api_key = key
    return sh


def test_non_ip_target_is_rejected():
    result = _lookup("k").host_info("evil.com/#")
    assert result["status"] == "error"
    assert "IP address" in result["status_reason"]


def test_no_key_falls_back_to_internetdb():
    with patch("modules.shodan_lookup.requests.get",
               return_value=FakeResponse(payload=INTERNETDB_PAYLOAD)) as mock_get:
        result = _lookup("").host_info("45.33.32.156")
    assert mock_get.call_count == 1
    assert "internetdb.shodan.io" in mock_get.call_args[0][0]
    assert result["status"] == "ok"
    assert result["source"] == "internetdb"
    assert result["open_ports"] == [22, 80, 123, 31337]
    assert result["hostnames"] == ["scanme.nmap.org"]
    assert result["vulns"] == ["CVE-2021-44224", "CVE-2019-0220"]


def test_paid_membership_403_falls_back_to_internetdb():
    responses = [FakeResponse(status_code=403), FakeResponse(payload=INTERNETDB_PAYLOAD)]
    with patch("modules.shodan_lookup.requests.get", side_effect=responses):
        result = _lookup("free-key").host_info("45.33.32.156")
    assert result["status"] == "ok"
    assert result["source"] == "internetdb"
    assert "paid membership" in result["status_reason"]
    assert result["open_ports"] == [22, 80, 123, 31337]


def test_rate_limit_falls_back_to_internetdb():
    responses = [FakeResponse(status_code=429), FakeResponse(payload=INTERNETDB_PAYLOAD)]
    with patch("modules.shodan_lookup.requests.get", side_effect=responses):
        result = _lookup("k").host_info("45.33.32.156")
    assert result["status"] == "ok"
    assert result["source"] == "internetdb"


def test_paid_key_still_uses_shodan():
    payload = {"org": "Linode", "isp": "Linode", "ports": [22, 80],
               "data": [{"port": 22, "product": "OpenSSH"}], "vulns": {"CVE-1": {}}}
    with patch("modules.shodan_lookup.requests.get",
               return_value=FakeResponse(payload=payload)) as mock_get:
        result = _lookup("paid-key").host_info("45.33.32.156")
    assert mock_get.call_count == 1
    assert "api.shodan.io" in mock_get.call_args[0][0]
    assert result["source"] == "shodan"
    assert result["organization"] == "Linode"
    assert result["services"][0]["product"] == "OpenSSH"


def test_invalid_key_does_not_fall_back():
    with patch("modules.shodan_lookup.requests.get",
               return_value=FakeResponse(status_code=401)) as mock_get:
        result = _lookup("bad").host_info("45.33.32.156")
    assert mock_get.call_count == 1
    assert result["status"] == "error"


def test_internetdb_404_is_ok_with_nothing_known():
    with patch("modules.shodan_lookup.requests.get", return_value=FakeResponse(status_code=404)):
        result = _lookup("").host_info("45.33.32.156")
    assert result["status"] == "ok"
    assert result["open_ports"] == []
    assert "nothing on this address" in result["status_reason"]


def test_internetdb_unreachable_is_skipped_not_an_error():
    with patch("modules.shodan_lookup.requests.get", side_effect=OSError("network down")):
        result = _lookup("").host_info("45.33.32.156")
    assert result["status"] == "skipped"


@pytest.mark.parametrize("ip", ["1.1.1.1", "2606:4700:4700::1111"])
def test_ipv4_and_ipv6_are_accepted(ip):
    with patch("modules.shodan_lookup.requests.get", return_value=FakeResponse(payload={"ports": []})):
        result = _lookup("").host_info(ip)
    assert result["status"] == "ok"
