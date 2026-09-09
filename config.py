import os
from dotenv import load_dotenv

load_dotenv()

NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")
LEAK_LOOKUP_API_KEY = os.getenv("LEAK_LOOKUP_API_KEY", "")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")
IPINFO_API_KEY = os.getenv("IPINFO_API_KEY", "")

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CENSYS_API_ID = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET", "")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Single outbound identity for all modules. Kept in one place so version bumps
# don't leave half the modules announcing a stale release.
PRISM_VERSION = "2.8.1"
USER_AGENT = f"PRISM-OSINT/{PRISM_VERSION} (+https://github.com/NovaCode37/Prism-platform)"

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
