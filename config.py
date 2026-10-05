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

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

LLM_API_KEY = os.getenv("LLM_API_KEY") or OPENROUTER_API_KEY or GROQ_API_KEY
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or (OPENROUTER_URL if OPENROUTER_API_KEY else GROQ_URL)
LLM_MODEL = os.getenv("LLM_MODEL") or ("nvidia/nemotron-3-nano-30b-a3b:free" if OPENROUTER_API_KEY else "llama-3.1-8b-instant")
LLM_PROXY = os.getenv("LLM_PROXY", "").strip()
LLM_PROXIES = {"http": LLM_PROXY, "https": LLM_PROXY} if LLM_PROXY else None
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)
PRISM_VERSION = "2.11.0"
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
