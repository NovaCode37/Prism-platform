import requests
from typing import Dict, Any


class QRDecoder:

    def decode(self, image_bytes: bytes, filename: str = "qr.png") -> Dict[str, Any]:
        result = {
            "decoded": None,
            "type": None,
            "is_url": False,
            "error": None,
        }
        try:
            r = requests.post(
                "https://api.qrserver.com/v1/read-qr-code/",
                files={"file": (filename, image_bytes)},
                timeout=15,
            )
            if r.status_code != 200:
                result["error"] = f"API returned HTTP {r.status_code}"
                return result

            data = r.json()
            if not data or not isinstance(data, list):
                result["error"] = "Unexpected API response"
                return result

            symbols = data[0].get("symbol", [])
            if not symbols:
                result["error"] = "No QR code detected in the image"
                return result

            error = symbols[0].get("error")
            if error:
                result["error"] = error
                return result

            decoded = symbols[0].get("data", "")
            result["decoded"] = decoded

            if decoded.startswith(("http://", "https://")):
                result["is_url"] = True
                result["type"] = "URL"
            elif decoded.startswith("WIFI:"):
                result["type"] = "Wi-Fi credentials"
            elif decoded.startswith("BEGIN:VCARD") or decoded.startswith("MECARD:"):
                result["type"] = "Contact (vCard)"
            elif decoded.startswith("BEGIN:VEVENT"):
                result["type"] = "Calendar event"
            elif decoded.startswith("mailto:"):
                result["type"] = "Email"
            elif decoded.startswith("tel:"):
                result["type"] = "Phone number"
            elif decoded.startswith("geo:"):
                result["type"] = "Geolocation"
            elif decoded.startswith("bitcoin:") or decoded.startswith("ethereum:"):
                result["type"] = "Crypto address"
            else:
                result["type"] = "Plain text"

        except Exception as e:
            result["error"] = str(e)

        return result
