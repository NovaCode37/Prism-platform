import base64
import time
import requests
from typing import Dict, Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import VIRUSTOTAL_API_KEY


class URLScanner:
    VT_BASE = "https://www.virustotal.com/api/v3"

    def scan(self, url: str) -> Dict[str, Any]:
        result = {
            "url": url,
            "status": None,
            "malicious": 0,
            "suspicious": 0,
            "harmless": 0,
            "undetected": 0,
            "categories": {},
            "permalink": None,
            "error": None,
        }

        if not VIRUSTOTAL_API_KEY:
            result["error"] = "No VirusTotal API key configured (add VIRUSTOTAL_API_KEY to .env)"
            return result

        headers = {"x-apikey": VIRUSTOTAL_API_KEY}

        try:
            r = requests.post(
                f"{self.VT_BASE}/urls",
                headers=headers,
                data={"url": url},
                timeout=15,
                verify=False,
            )
            if r.status_code not in (200, 201):
                result["error"] = f"Submit failed: HTTP {r.status_code}"
                return result

            analysis_id = r.json().get("data", {}).get("id")
            if not analysis_id:
                result["error"] = "No analysis ID returned"
                return result
        except Exception as e:
            result["error"] = str(e)
            return result

        for _ in range(20):
            time.sleep(5)
            try:
                r2 = requests.get(
                    f"{self.VT_BASE}/analyses/{analysis_id}",
                    headers=headers,
                    timeout=15,
                    verify=False,
                )
                data = r2.json().get("data", {})
                attrs = data.get("attributes", {})
                if attrs.get("status") == "completed":
                    stats = attrs.get("stats", {})
                    result["status"] = "completed"
                    result["malicious"] = stats.get("malicious", 0)
                    result["suspicious"] = stats.get("suspicious", 0)
                    result["harmless"] = stats.get("harmless", 0)
                    result["undetected"] = stats.get("undetected", 0)
                    result["categories"] = attrs.get("categories", {})
                    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
                    result["permalink"] = f"https://www.virustotal.com/gui/url/{url_id}"
                    return result
            except Exception as e:
                result["error"] = str(e)
                return result

        result["status"] = "timeout"
        result["error"] = "Analysis timed out — try checking VirusTotal directly"
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        result["permalink"] = f"https://www.virustotal.com/gui/url/{url_id}"
        return result
