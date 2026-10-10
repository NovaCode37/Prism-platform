from unittest.mock import patch

import phonenumbers

from modules.hlr_lookup import HLRLookup
from modules.module_status import ERROR, OK


def _hlr():
    hlr = HLRLookup()
    hlr.api_key = None
    return hlr


def test_valid_number_is_ok():
    result = _hlr().validate_phone("+14155552671")
    assert result["status"] == OK
    assert result["error"] is None
    assert result["valid"] is True


def test_invalid_but_parseable_number_is_ok():
    result = _hlr().validate_phone("+1234")
    assert result["status"] == OK
    assert result["error"] is None
    assert result["valid"] is False


def test_parse_failure_is_error():
    result = _hlr().validate_phone("not a number")
    assert result["status"] == ERROR
    assert result["error"].startswith("Parse error:")
    assert result["status_reason"] == result["error"]


def test_unexpected_exception_is_error():
    hlr = _hlr()
    with patch.object(phonenumbers, "is_valid_number", side_effect=RuntimeError("boom")):
        result = hlr.validate_phone("+14155552671")
    assert result["status"] == ERROR
    assert result["error"] == "boom"
