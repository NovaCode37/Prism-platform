import os
import urllib3
import requests
from dotenv import load_dotenv

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_send = requests.Session.send
def _send_no_verify(self, r, **kwargs):
    kwargs["verify"] = False
    return _orig_send(self, r, **kwargs)
requests.Session.send = _send_no_verify

EMAILREP_API_KEY = os.getenv("EMAILREP_API_KEY", "")
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")
LEAK_LOOKUP_API_KEY = os.getenv("LEAK_LOOKUP_API_KEY", "")
IPINFO_API_KEY = os.getenv("IPINFO_API_KEY", "")

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ███████╗██╗███╗   ██╗████████╗                     ║
║  ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝                     ║
║  ██║   ██║███████╗██║██╔██╗ ██║   ██║                        ║
║  ██║   ██║╚════██║██║██║╚██╗██║   ██║                        ║
║  ╚██████╔╝███████║██║██║ ╚████║   ██║                        ║
║   ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝                        ║
║                                                               ║
║           Open Source Intelligence Toolkit v2.0               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)
