import re
import socket
from email import message_from_string
from typing import Dict, Any, List, Optional
import requests

def _reverse_dns(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None

def _parse_received_ip(line: str) -> Optional[str]:
    ip_re = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
    matches = ip_re.findall(line)
    for ip in matches:
        parts = [int(p) for p in ip.split('.')]
        if parts[0] == 10:
            continue
        if parts[0] == 127:
            continue
        if parts[0] == 192 and parts[1] == 168:
            continue
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            continue
        return ip
    return None

def _geoip(ip: str) -> Dict:
    try:
        r = requests.get(f'https://ipinfo.io/{ip}/json', timeout=6)
        if r.status_code == 200:
            d = r.json()
            return {
                'city': d.get('city'),
                'region': d.get('region'),
                'country': d.get('country'),
                'org': d.get('org'),
                'loc': d.get('loc'),
            }
    except Exception:
        pass
    return {}

def analyze_headers(raw_headers: str) -> Dict[str, Any]:
    result = {
        'from': None,
        'to': None,
        'subject': None,
        'date': None,
        'message_id': None,
        'reply_to': None,
        'x_mailer': None,
        'spf': None,
        'dkim': None,
        'dmarc': None,
        'hops': [],
        'origin_ip': None,
        'origin_geo': {},
        'origin_rdns': None,
        'spoofing_flags': [],
        'error': None,
    }

    try:
        msg = message_from_string(raw_headers)

        result['from']       = msg.get('From')
        result['to']         = msg.get('To')
        result['subject']    = msg.get('Subject')
        result['date']       = msg.get('Date')
        result['message_id'] = msg.get('Message-ID')
        result['reply_to']   = msg.get('Reply-To')
        result['x_mailer']   = msg.get('X-Mailer') or msg.get('X-MimeOLE')

        auth_results = msg.get('Authentication-Results') or ''
        received_spf = msg.get('Received-SPF') or ''

        spf_match = re.search(r'spf=(\w+)', auth_results, re.IGNORECASE) or \
                    re.search(r'^(pass|fail|softfail|neutral|none)', received_spf, re.IGNORECASE)
        if spf_match:
            result['spf'] = spf_match.group(1).lower()

        dkim_match = re.search(r'dkim=(\w+)', auth_results, re.IGNORECASE)
        if dkim_match:
            result['dkim'] = dkim_match.group(1).lower()

        dmarc_match = re.search(r'dmarc=(\w+)', auth_results, re.IGNORECASE)
        if dmarc_match:
            result['dmarc'] = dmarc_match.group(1).lower()

        received_headers = msg.get_all('Received') or []
        hops = []
        for r_hdr in reversed(received_headers):
            r_hdr_clean = r_hdr.replace('\n', ' ').replace('\t', ' ')
            ip = _parse_received_ip(r_hdr_clean)
            by_match = re.search(r'by\s+([\w.\-]+)', r_hdr_clean, re.IGNORECASE)
            from_match = re.search(r'from\s+([\w.\-]+)', r_hdr_clean, re.IGNORECASE)
            date_match = re.search(r';\s*(.+)$', r_hdr_clean)
            hop = {
                'from_host': from_match.group(1) if from_match else None,
                'by_host': by_match.group(1) if by_match else None,
                'ip': ip,
                'date': date_match.group(1).strip() if date_match else None,
                'geo': {},
                'rdns': None,
            }
            if ip:
                hop['geo'] = _geoip(ip)
                hop['rdns'] = _reverse_dns(ip)
            hops.append(hop)

        result['hops'] = hops

        if hops:
            first_hop = next((h for h in hops if h['ip']), None)
            if first_hop:
                result['origin_ip'] = first_hop['ip']
                result['origin_geo'] = first_hop['geo']
                result['origin_rdns'] = first_hop['rdns']

        flags = []
        if result['from'] and result['reply_to']:
            from_domain = re.search(r'@([\w.\-]+)', result['from'])
            reply_domain = re.search(r'@([\w.\-]+)', result['reply_to'])
            if from_domain and reply_domain and from_domain.group(1) != reply_domain.group(1):
                flags.append({'type': 'REPLY_TO_MISMATCH',
                               'detail': f"From domain {from_domain.group(1)} != Reply-To {reply_domain.group(1)}"})
        if result['spf'] in ('fail', 'softfail'):
            flags.append({'type': 'SPF_FAIL', 'detail': f"SPF result: {result['spf']}"})
        if result['dkim'] and result['dkim'] not in ('pass',):
            flags.append({'type': 'DKIM_FAIL', 'detail': f"DKIM result: {result['dkim']}"})
        if result['dmarc'] and result['dmarc'] not in ('pass',):
            flags.append({'type': 'DMARC_FAIL', 'detail': f"DMARC result: {result['dmarc']}"})

        result['spoofing_flags'] = flags

    except Exception as e:
        result['error'] = str(e)

    return result
