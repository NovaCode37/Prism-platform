import ipaddress
import re
from typing import Any, Dict, List, Optional

import requests

from modules.module_status import annotate, OK, SKIPPED, ERROR

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"


class RDAPLookup:
    def __init__(self, timeout: int = 15, use_bootstrap: bool = True):
        self.timeout = timeout
        self.use_bootstrap = use_bootstrap
        self._bootstrap_cache: Optional[Dict[str, str]] = None

    def _load_bootstrap(self) -> Dict[str, str]:
        if self._bootstrap_cache is not None:
            return self._bootstrap_cache
        try:
            r = requests.get(IANA_BOOTSTRAP_URL, timeout=self.timeout)
            if r.status_code != 200:
                return {}
            data = r.json()
            services = data.get("services", [])
            tld_map: Dict[str, str] = {}
            for service in services:
                if not isinstance(service, list) or len(service) < 2:
                    continue
                tlds = service[0] if isinstance(service[0], list) else []
                urls = service[1] if isinstance(service[1], list) else []
                if not tlds or not urls:
                    continue
                rdap_url = urls[0]
                for tld in tlds:
                    if isinstance(tld, str):
                        tld_map[tld.lower()] = rdap_url
            self._bootstrap_cache = tld_map
            return tld_map
        except Exception:
            return {}

    def _get_rdap_url(self, domain: str) -> str:
        domain_lower = domain.lower().strip()
        domain = domain_lower.rstrip(".")
        parts = domain.split(".")
        tld = parts[-1].lower() if parts else ""
        if self.use_bootstrap:
            tld_map = self._load_bootstrap()
            if tld in tld_map:
                base_url = tld_map[tld]
                if not base_url.endswith("/"):
                    base_url += "/"
                return f"{base_url}domain/{domain}"
        return f"https://rdap.org/domain/{domain}"

    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
            return date_str
        return date_str

    def _parse_contact(self, entity: Dict[str, Any]) -> Dict[str, Optional[str]]:
        contact = {
            "name": None,
            "email": None,
            "phone": None,
            "organization": None,
            "country": None,
        }
        contact["name"] = entity.get("fn") or entity.get("handle")
        vcard = entity.get("vcardArray", [])
        if len(vcard) > 1 and isinstance(vcard[1], list):
            for prop in vcard[1]:
                if not isinstance(prop, list) or len(prop) < 3:
                    continue
                prop_name = prop[0]
                prop_value = prop[2] if len(prop) > 2 else None
                if prop_name == "fn":
                    contact["name"] = prop_value
                elif prop_name == "email":
                    contact["email"] = prop_value
                elif prop_name == "tel":
                    contact["phone"] = prop_value
                elif prop_name == "org":
                    contact["organization"] = prop_value
                elif prop_name == "adr" and isinstance(prop_value, list) and len(prop_value) > 6:
                    contact["country"] = prop_value[6]
        if not contact["organization"]:
            contact["organization"] = entity.get("org")
        return contact

    def lookup(self, domain: str) -> Dict[str, Any]:
        domain = (domain or "").strip().lower()
        domain = domain.rstrip(".")
        result: Dict[str, Any] = {
            "domain": domain,
            "rdap_url": None,
            "registered": None,
            "created": None,
            "expires": None,
            "updated": None,
            "registrar": None,
            "registrant": None,
            "administrative": None,
            "technical": None,
            "nameservers": [],
            "raw": None,
            "error": None,
        }
        if not domain:
            return annotate(result, ERROR, "No domain provided")
        if not re.match(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", domain):
            return annotate(result, ERROR, f"Invalid domain format: {domain}")

        rdap_url = self._get_rdap_url(domain)
        result["rdap_url"] = rdap_url

        try:
            r = requests.get(
                rdap_url,
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "PRISM-OSINT/2.1"},
            )
            if r.status_code == 404:
                result["registered"] = False
                return annotate(result, OK, "Domain is not registered")
            if r.status_code == 403:
                return annotate(result, SKIPPED, "RDAP server refused the request (access denied)")
            if r.status_code == 429:
                return annotate(result, SKIPPED, "RDAP server rate limited the request")

            if r.status_code != 200:
                if r.status_code in (301, 302, 303, 307, 308):
                    location = r.headers.get("location")
                    if location:
                        result["rdap_url"] = location
                        try:
                            r2 = requests.get(
                                location,
                                timeout=self.timeout,
                                headers={"Accept": "application/json", "User-Agent": "PRISM-OSINT/2.1"},
                            )
                            if r2.status_code == 200:
                                r = r2
                            else:
                                return annotate(result, SKIPPED, f"RDAP unavailable for this TLD (HTTP {r.status_code})")
                        except Exception:
                            return annotate(result, SKIPPED, "RDAP unavailable for this TLD")
                    else:
                        return annotate(result, SKIPPED, f"RDAP unavailable for this TLD (HTTP {r.status_code})")
                else:
                    return annotate(result, SKIPPED, f"RDAP unavailable (HTTP {r.status_code})")

            data = r.json()
            result["registered"] = True

            events = data.get("events", [])
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    action = event.get("eventAction") or event.get("action")
                    date = event.get("eventDate") or event.get("date")
                    if action == "registration":
                        result["created"] = self._format_date(date)
                    elif action == "expiration":
                        result["expires"] = self._format_date(date)
                    elif action == "last changed" or action == "lastChanged":
                        result["updated"] = self._format_date(date)

            entities = data.get("entities", [])
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                roles = entity.get("roles") or entity.get("role") or []
                if not isinstance(roles, list):
                    roles = [roles] if roles else []
                if "registrar" in roles or "registrar" in entity.get("type", "").lower():
                    result["registrar"] = entity.get("fn") or entity.get("handle")
                if "registrant" in roles:
                    result["registrant"] = self._parse_contact(entity)
                if "administrative" in roles or "admin" in roles:
                    result["administrative"] = self._parse_contact(entity)
                if "technical" in roles:
                    result["technical"] = self._parse_contact(entity)

            nameservers = data.get("nameservers", [])
            if isinstance(nameservers, list):
                for ns in nameservers:
                    if isinstance(ns, dict):
                        ns_name = ns.get("ldhName") or ns.get("fqdn") or ns.get("name")
                        if ns_name:
                            result["nameservers"].append(ns_name)

            result["raw"] = data
            return annotate(result, OK)

        except requests.Timeout:
            return annotate(result, SKIPPED, "RDAP request timed out")
        except requests.ConnectionError:
            return annotate(result, SKIPPED, "RDAP connection error")
        except Exception as e:
            return annotate(result, ERROR, str(e)[:200])


def run_rdap_lookup(domain: str) -> Dict[str, Any]:
    rdap = RDAPLookup()
    return rdap.lookup(domain)