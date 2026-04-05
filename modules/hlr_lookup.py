import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from typing import Dict, Any, Optional
import sys
sys.path.append('..')
from config import NUMVERIFY_API_KEY, Colors

class HLRLookup:
    
    def __init__(self):
        self.api_key = NUMVERIFY_API_KEY
        self.numverify_url = "http://apilayer.net/api/validate"
    
    def validate_phone(self, phone: str, country_code: str = None) -> Dict[str, Any]:
        result = {
            "phone": phone,
            "valid": False,
            "carrier": None,
            "country": None,
            "region": None,
            "timezones": [],
            "line_type": None,
            "formatted": None,
            "error": None
        }
        
        try:
            if country_code:
                parsed = phonenumbers.parse(phone, country_code)
            else:
                if not phone.startswith('+'):
                    phone = '+' + phone
                parsed = phonenumbers.parse(phone)
            
            result["valid"] = phonenumbers.is_valid_number(parsed)
            result["formatted"] = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            
            result["carrier"] = carrier.name_for_number(parsed, "en")

            region_code = phonenumbers.region_code_for_number(parsed)
            result["country_code"] = region_code
            result["region"] = geocoder.description_for_number(parsed, "en")
            # Use region_code to get country name; fall back to geocoder description
            from phonenumbers import PhoneMetadata
            _country_names = {
                "US": "United States", "GB": "United Kingdom", "DE": "Germany",
                "FR": "France", "RU": "Russia", "CN": "China", "JP": "Japan",
                "IN": "India", "BR": "Brazil", "AU": "Australia", "CA": "Canada",
                "IT": "Italy", "ES": "Spain", "NL": "Netherlands", "SE": "Sweden",
                "NO": "Norway", "DK": "Denmark", "FI": "Finland", "PL": "Poland",
                "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "PT": "Portugal",
                "IE": "Ireland", "CZ": "Czech Republic", "GR": "Greece", "TR": "Turkey",
                "KR": "South Korea", "MX": "Mexico", "AR": "Argentina", "CO": "Colombia",
                "ZA": "South Africa", "UA": "Ukraine", "KZ": "Kazakhstan", "IL": "Israel",
                "AE": "United Arab Emirates", "SA": "Saudi Arabia", "TH": "Thailand",
                "VN": "Vietnam", "PH": "Philippines", "ID": "Indonesia", "MY": "Malaysia",
                "SG": "Singapore", "NZ": "New Zealand", "HK": "Hong Kong", "TW": "Taiwan",
            }
            result["country"] = _country_names.get(region_code, region_code or geocoder.description_for_number(parsed, "en"))
            
            result["timezones"] = list(timezone.time_zones_for_number(parsed))
            
            number_type = phonenumbers.number_type(parsed)
            type_map = {
                phonenumbers.PhoneNumberType.MOBILE: "Mobile",
                phonenumbers.PhoneNumberType.FIXED_LINE: "Fixed Line",
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
                phonenumbers.PhoneNumberType.TOLL_FREE: "Toll Free",
                phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium Rate",
                phonenumbers.PhoneNumberType.VOIP: "VoIP",
                phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Personal",
                phonenumbers.PhoneNumberType.UNKNOWN: "Unknown"
            }
            result["line_type"] = type_map.get(number_type, "Unknown")
            
            if self.api_key:
                api_result = self._numverify_lookup(phone)
                if api_result:
                    result.update(api_result)
                    
        except phonenumbers.NumberParseException as e:
            result["error"] = f"Parse error: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _numverify_lookup(self, phone: str) -> Optional[Dict]:
        try:
            params = {
                "access_key": self.api_key,
                "number": phone.replace("+", "").replace(" ", ""),
                "format": 1
            }
            response = requests.get(self.numverify_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    return {
                        "country_code": data.get("country_code"),
                        "country_name": data.get("country_name"),
                        "location": data.get("location"),
                        "carrier": data.get("carrier") or None,
                        "line_type": data.get("line_type")
                    }
        except Exception:
            pass
        return None
    
    def print_result(self, result: Dict):
        print(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}")
        print(f"{Colors.BOLD}HLR Lookup Result{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}")
        
        if result.get("error"):
            print(f"{Colors.RED}Error: {result['error']}{Colors.RESET}")
            return
        
        status = f"{Colors.GREEN}✓ Valid{Colors.RESET}" if result["valid"] else f"{Colors.RED}✗ Invalid{Colors.RESET}"
        
        print(f"{Colors.YELLOW}Phone:{Colors.RESET} {result.get('formatted', result['phone'])}")
        print(f"{Colors.YELLOW}Status:{Colors.RESET} {status}")
        print(f"{Colors.YELLOW}Type:{Colors.RESET} {result.get('line_type', 'N/A')}")
        print(f"{Colors.YELLOW}Carrier:{Colors.RESET} {result.get('carrier') or 'N/A'}")
        print(f"{Colors.YELLOW}Country:{Colors.RESET} {result.get('country') or result.get('country_name', 'N/A')}")
        print(f"{Colors.YELLOW}Region:{Colors.RESET} {result.get('region') or result.get('location', 'N/A')}")
        
        if result.get("timezones"):
            print(f"{Colors.YELLOW}Timezones:{Colors.RESET} {', '.join(result['timezones'])}")

    def reverse_lookup(self, phone: str) -> Dict[str, Any]:
        result = {
            "phone": phone,
            "names": [],
            "city": None,
            "carrier_confirmed": None,
            "comments": [],
            "sources": [],
            "error": None,
        }

        clean = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        try:
            r = requests.get(
                f"https://api.numlookupapi.com/v1/validate/{clean}",
                headers={"User-Agent": "OSINT-Toolkit/2.0"},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("city"):
                    result["city"] = data["city"]
                if data.get("carrier"):
                    result["carrier_confirmed"] = data["carrier"]
                result["sources"].append("numlookupapi.com")
        except Exception:
            pass

        is_ru = clean.startswith("7") or clean.startswith("89") or clean.startswith("87")
        if is_ru:
            if clean.startswith("7"):
                ru_num = clean[1:]
            elif clean.startswith("89") or clean.startswith("87"):
                ru_num = clean[1:]
            else:
                ru_num = clean

            for site_url, site_name in [
                (f"https://kto-zvonil.ru/nomer/7{ru_num}/", "kto-zvonil.ru"),
                (f"https://zvonili.com/phone/7{ru_num}/", "zvonili.com"),
            ]:
                try:
                    import re
                    r = requests.get(
                        site_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                        timeout=8,
                    )
                    if r.status_code == 200:
                        text = r.text
                        name_matches = re.findall(
                            r'(?:владелец|зарегистрирован на|Имя абонента|owner_name)[^\w]*:?\s*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})',
                            text
                        )
                        for n in name_matches[:3]:
                            if n not in result["names"]:
                                result["names"].append(n)
                        comments = re.findall(
                            r'<(?:p|div|span)[^>]*class="[^"]*comment[^"]*"[^>]*>([^<]{10,120})<',
                            text, re.IGNORECASE
                        )
                        for c in comments[:3]:
                            c = c.strip()
                            if c and c not in result["comments"]:
                                result["comments"].append(c)
                        result["sources"].append(site_name)
                except Exception:
                    pass

        return result


def run_hlr_lookup():
    hlr = HLRLookup()
    
    print(f"\n{Colors.BOLD}HLR Lookup - Mobile Number Checker{Colors.RESET}")
    print(f"{Colors.CYAN}Enter phone number with country code (e.g., +79001234567){Colors.RESET}")
    
    phone = input(f"\n{Colors.GREEN}Phone number: {Colors.RESET}").strip()
    
    if not phone:
        print(f"{Colors.RED}No phone number provided{Colors.RESET}")
        return None
    
    result = hlr.validate_phone(phone)
    hlr.print_result(result)
    
    return result

if __name__ == "__main__":
    run_hlr_lookup()
