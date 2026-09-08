import os
from typing import Dict, Optional

def get_proxies() -> Optional[Dict[str, str]]:
    proxy = os.getenv("MODULE_PROXY", "").strip()
    if proxy:
        return {"http": proxy, "https": proxy}
    return None
