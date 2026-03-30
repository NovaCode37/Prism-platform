RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/main.py"
VENV_DIR="$SCRIPT_DIR/venv"

print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   ██████╗ ███████╗██╗███╗   ██╗████████╗                     ║"
    echo "║  ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝                     ║"
    echo "║  ██║   ██║███████╗██║██╔██╗ ██║   ██║                        ║"
    echo "║  ██║   ██║╚════██║██║██║╚██╗██║   ██║                        ║"
    echo "║  ╚██████╔╝███████║██║██║ ╚████║   ██║                        ║"
    echo "║   ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝                        ║"
    echo "║                                                               ║"
    echo "║           Open Source Intelligence Toolkit v1.0               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Python not found. Please install Python 3.8+${NC}"
        exit 1
    fi
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
    fi
}

install_deps() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r "$SCRIPT_DIR/requirements.txt" -q
    echo -e "${GREEN}Dependencies installed!${NC}"
}

show_help() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./osint.sh                    # Interactive mode"
    echo "  ./osint.sh -t <target>        # Quick scan target"
    echo "  ./osint.sh --install          # Install dependencies"
    echo ""
    echo -e "${BOLD}Quick Scan Examples:${NC}"
    echo "  ./osint.sh -t user@email.com  # Scan email"
    echo "  ./osint.sh -t +79001234567    # Scan phone"
    echo "  ./osint.sh -t johndoe         # Search username"
    echo "  ./osint.sh -t example.com     # Scan domain"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -t, --target <value>    Target to scan (auto-detects type)"
    echo "  --type <type>           Force target type: email|phone|username|domain|ip"
    echo "  -o, --output <file>     Save results to JSON file"
    echo "  --install               Install/update dependencies"
    echo "  -h, --help              Show this help"
    echo ""
    echo -e "${BOLD}Individual Tools (interactive):${NC}"
    echo "  ./osint.sh hlr          # HLR phone lookup"
    echo "  ./osint.sh hunter       # Hunter.io email search"
    echo "  ./osint.sh blackbird    # Username search (fast)"
    echo "  ./osint.sh maigret      # Username search (deep)"
    echo "  ./osint.sh leak         # Breach lookup"
    echo "  ./osint.sh smtp         # SMTP email verify"
    echo "  ./osint.sh whois        # WHOIS lookup"
    echo "  ./osint.sh geoip        # GeoIP lookup"
    echo "  ./osint.sh dns          # DNS records"
    echo "  ./osint.sh web          # Website analysis"
}

run_tool() {
    local tool=$1
    shift
    
    case $tool in
        hlr)
            $PYTHON_CMD -c "from modules.hlr_lookup import run_hlr_lookup; run_hlr_lookup()"
            ;;
        hunter)
            $PYTHON_CMD -c "from modules.hunter import run_hunter_domain; run_hunter_domain()"
            ;;
        blackbird)
            $PYTHON_CMD -c "from modules.blackbird import run_blackbird; run_blackbird()"
            ;;
        maigret)
            $PYTHON_CMD -c "from modules.maigret_wrapper import run_maigret; run_maigret()"
            ;;
        leak)
            $PYTHON_CMD -c "from modules.leak_lookup import run_leak_lookup; run_leak_lookup()"
            ;;
        smtp)
            $PYTHON_CMD -c "from modules.smtp_verify import run_smtp_verify; run_smtp_verify()"
            ;;
        whois)
            $PYTHON_CMD -c "from modules.extra_tools import run_whois; run_whois()"
            ;;
        geoip)
            $PYTHON_CMD -c "from modules.extra_tools import run_geoip; run_geoip()"
            ;;
        dns)
            $PYTHON_CMD -c "from modules.extra_tools import run_dns; run_dns()"
            ;;
        web)
            $PYTHON_CMD -c "from modules.extra_tools import run_website_analysis; run_website_analysis()"
            ;;
        *)
            echo -e "${RED}Unknown tool: $tool${NC}"
            show_help
            exit 1
            ;;
    esac
}

main() {
    cd "$SCRIPT_DIR"
    check_python
    
    case "${1:-}" in
        -h|--help)
            print_banner
            show_help
            exit 0
            ;;
        --install)
            setup_venv
            install_deps
            exit 0
            ;;
        hlr|hunter|blackbird|maigret|leak|smtp|whois|geoip|dns|web)
            setup_venv
            run_tool "$@"
            exit 0
            ;;
        -t|--target)
            setup_venv
            $PYTHON_CMD "$PYTHON_SCRIPT" "$@"
            exit 0
            ;;
        "")
            setup_venv
            $PYTHON_CMD "$PYTHON_SCRIPT"
            exit 0
            ;;
        *)
            setup_venv
            $PYTHON_CMD "$PYTHON_SCRIPT" "$@"
            exit 0
            ;;
    esac
}

main "$@"
