from unittest.mock import MagicMock, patch

from modules.module_status import ERROR, OK
from modules.qr_decoder import QRDecoder


def _api_response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_local_decode_is_ok():
    decoder = QRDecoder()
    with patch.object(decoder, "_decode_local", return_value="https://example.com"):
        result = decoder.decode(b"img")
    assert result["status"] == OK
    assert result["error"] is None
    assert result["decoded"] == "https://example.com"
    assert result["is_url"] is True
    assert result["source"] == "local"


def test_no_qr_code_is_ok_with_reason():
    decoder = QRDecoder()
    with patch.object(decoder, "_decode_local", return_value=None), patch(
        "modules.qr_decoder.requests.post",
        return_value=_api_response([{"symbol": []}]),
    ):
        result = decoder.decode(b"img")
    assert result["status"] == OK
    assert result["status_reason"] == "No QR code detected in the image"
    assert result["error"] is None
    assert result["decoded"] is None


def test_api_http_error_is_error():
    decoder = QRDecoder()
    with patch.object(decoder, "_decode_local", return_value=None), patch(
        "modules.qr_decoder.requests.post",
        return_value=_api_response(None, status_code=500),
    ):
        result = decoder.decode(b"img")
    assert result["status"] == ERROR
    assert result["error"] == "API returned HTTP 500"


def test_api_exception_is_error():
    decoder = QRDecoder()
    with patch.object(decoder, "_decode_local", return_value=None), patch(
        "modules.qr_decoder.requests.post", side_effect=ConnectionError("network down")
    ):
        result = decoder.decode(b"img")
    assert result["status"] == ERROR
    assert result["error"] == "network down"


def test_api_decode_is_ok():
    decoder = QRDecoder()
    with patch.object(decoder, "_decode_local", return_value=None), patch(
        "modules.qr_decoder.requests.post",
        return_value=_api_response([{"symbol": [{"data": "hello", "error": None}]}]),
    ):
        result = decoder.decode(b"img")
    assert result["status"] == OK
    assert result["decoded"] == "hello"
    assert result["type"] == "Plain text"
    assert result["source"] == "api"
