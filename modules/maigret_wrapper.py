import subprocess
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
sys.path.append('..')
from config import OUTPUT_DIR, Colors

class MaigretWrapper:

    def __init__(self):
        self.maigret_bin = self._find_maigret()
        self.maigret_installed = self.maigret_bin is not None

    def _find_maigret(self) -> Optional[str]:
        custom = os.getenv("MAIGRET_BIN")
        if custom and os.path.isfile(custom):
            return custom

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(project_root, "venv-maigret", "bin", "maigret"),
            os.path.join(project_root, "venv-maigret", "Scripts", "maigret.exe"),
            "maigret",
        ]
        for path in candidates:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None

    def install_maigret(self) -> bool:
        print(f"{Colors.YELLOW}Installing maigret into isolated venv...{Colors.RESET}")
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            venv_path = os.path.join(project_root, "venv-maigret")
            if not os.path.isdir(venv_path):
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True, timeout=30)
            pip_bin = os.path.join(venv_path, "Scripts", "pip.exe") if sys.platform == "win32" \
                else os.path.join(venv_path, "bin", "pip")
            result = subprocess.run(
                [pip_bin, "install", "maigret"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                self.maigret_bin = self._find_maigret()
                self.maigret_installed = self.maigret_bin is not None
                print(f"{Colors.GREEN}Maigret installed successfully{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}Failed to install maigret: {result.stderr}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Error installing maigret: {e}{Colors.RESET}")
            return False

    def search(self, username: str, output_formats: List[str] = None,
               timeout: int = 30, top_sites: int = 500) -> Dict[str, Any]:
        if not self.maigret_installed:
            if not self.install_maigret():
                return {"error": "Maigret not installed and installation failed"}

        result = {
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "accounts": [],
            "output_files": [],
            "error": None
        }

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"maigret_{username}_{timestamp}"
        output_path = os.path.join(OUTPUT_DIR, base_filename)

        cmd = [
            self.maigret_bin, username,
            "--timeout", str(timeout),
            "--top-sites", str(top_sites),
            "--retries", "1",
            "--no-color"
        ]

        if output_formats:
            for fmt in output_formats:
                if fmt == "json":
                    cmd.extend(["--json", f"{output_path}.json"])
                    result["output_files"].append(f"{output_path}.json")
                elif fmt == "html":
                    cmd.extend(["--html", f"{output_path}.html"])
                    result["output_files"].append(f"{output_path}.html")
                elif fmt == "csv":
                    cmd.extend(["--csv", f"{output_path}.csv"])
                    result["output_files"].append(f"{output_path}.csv")
                elif fmt == "txt":
                    cmd.extend(["--txt", f"{output_path}.txt"])
                    result["output_files"].append(f"{output_path}.txt")
                elif fmt == "pdf":
                    cmd.extend(["--pdf", f"{output_path}.pdf"])
                    result["output_files"].append(f"{output_path}.pdf")
        else:
            cmd.extend(["--json", f"{output_path}.json"])
            result["output_files"].append(f"{output_path}.json")

        print(f"\n{Colors.CYAN}Running Maigret search for '{username}'...{Colors.RESET}")
        print(f"{Colors.YELLOW}Checking top {top_sites} sites (this may take a while){Colors.RESET}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            found_count = 0
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    if "[+]" in line or "found:" in line.lower():
                        found_count += 1
                        print(f"  {Colors.GREEN}{line}{Colors.RESET}")
                    elif "[-]" in line or "not found" in line.lower():
                        pass
                    elif "[!]" in line or "error" in line.lower():
                        print(f"  {Colors.YELLOW}{line}{Colors.RESET}")
                    else:
                        print(f"  {line}")

            process.wait()

            json_file = f"{output_path}.json"
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    if isinstance(json_data, dict) and "sites" in json_data:
                        for site_name, site_data in json_data["sites"].items():
                            if site_data.get("status", {}).get("status") == "Claimed":
                                result["accounts"].append({
                                    "site": site_name,
                                    "url": site_data.get("url_user", ""),
                                    "status": "found"
                                })

            result["total_found"] = len(result["accounts"])

        except subprocess.TimeoutExpired:
            result["error"] = "Search timed out"
        except Exception as e:
            result["error"] = str(e)

        return result

    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Maigret Search Results: {result['username']}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")

        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return

        print(f"{Colors.YELLOW}Accounts Found:{Colors.RESET} {Colors.GREEN}{result.get('total_found', 0)}{Colors.RESET}")

        if result.get("accounts"):
            print(f"\n{Colors.BOLD}Found Profiles:{Colors.RESET}")
            for acc in result["accounts"][:50]:
                print(f"  {Colors.GREEN}[+]{Colors.RESET} {acc['site']}: {Colors.CYAN}{acc['url']}{Colors.RESET}")

            if len(result["accounts"]) > 50:
                print(f"  ... and {len(result['accounts']) - 50} more")

        if result.get("output_files"):
            print(f"\n{Colors.BOLD}Output Files:{Colors.RESET}")
            for f in result["output_files"]:
                if os.path.exists(f):
                    print(f"  {Colors.GREEN}✓{Colors.RESET} {f}")

def run_maigret():
    maigret = MaigretWrapper()

    print(f"\n{Colors.BOLD}Maigret - Advanced Username Search{Colors.RESET}")
    print(f"{Colors.CYAN}Searches across 3000+ sites{Colors.RESET}")

    username = input(f"\n{Colors.GREEN}Enter username: {Colors.RESET}").strip()

    if not username:
        print(f"{Colors.RED}No username provided{Colors.RESET}")
        return None

    top_sites = input(f"{Colors.GREEN}Number of top sites to check (default 500): {Colors.RESET}").strip()
    top_sites = int(top_sites) if top_sites.isdigit() else 500

    formats = input(f"{Colors.GREEN}Output formats (json,html,csv,txt - comma separated, default: json): {Colors.RESET}").strip()
    formats = [f.strip() for f in formats.split(",")] if formats else ["json"]

    result = maigret.search(username, output_formats=formats, top_sites=top_sites)
    maigret.print_result(result)

    return result

if __name__ == "__main__":
    run_maigret()
