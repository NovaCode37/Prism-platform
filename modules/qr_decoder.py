import requests
from typing import Dict, Any, Optional, Tuple
from modules import get_proxies


class QRDecoder:

    def _decode_local(self, image_bytes: bytes) -> Optional[str]:
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
            return data or None
        except Exception:
            return None

    def _decode_api(self, image_bytes: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            proxies = get_proxies()
            r = requests.post(
                "https://api.qrserver.com/v1/read-qr-code/",
                files={"file": (filename, image_bytes)},
                timeout=15,
                proxies=proxies,  # Add this line
            )
            if r.status_code != 200:
                return None, f"API returned HTTP {r.status_code}"
            data = r.json()
            if not data or not isinstance(data, list):
                return None, "Unexpected API response"
            symbols = data[0].get("symbol", [])
            if not symbols:
                return None, "No QR code detected in the image"
            err = symbols[0].get("error")
            if err:
                return None, err
            return (symbols[0].get("data", "") or None), None
        except Exception as e:
            return None, str(e)

    def _classify(self, decoded: str) -> Tuple[str, bool]:
        if decoded.startswith(("http://", "https://")):
            return "URL", True
        if decoded.startswith("WIFI:"):
            return "Wi-Fi credentials", False
        if decoded.startswith("BEGIN:VCARD") or decoded.startswith("MECARD:"):
            return "Contact (vCard)", False
        if decoded.startswith("BEGIN:VEVENT"):
            return "Calendar event", False
        if decoded.startswith("mailto:"):
            return "Email", False
        if decoded.startswith("tel:"):
            return "Phone number", False
        if decoded.startswith("geo:"):
            return "Geolocation", False
        if decoded.startswith("bitcoin:") or decoded.startswith("ethereum:"):
            return "Crypto address", False
        return "Plain text", False

    def decode(self, image_bytes: bytes, filename: str = "qr.png") -> Dict[str, Any]:
        result = {
            "decoded": None,
            "type": None,
            "is_url": False,
            "source": None,
            "error": None,
        }

        decoded = self._decode_local(image_bytes)
        if decoded:
            result["source"] = "local"
        else:
            decoded, err = self._decode_api(image_bytes, filename)
            result["source"] = "api"
            if err:
                result["error"] = err
                return result

        if not decoded:
            result["error"] = "No QR code detected in the image"
            return result

        result["decoded"] = decoded
        result["type"], result["is_url"] = self._classify(decoded)
        return result
