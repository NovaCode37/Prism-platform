import re
import requests
from typing import Dict, Any

class CryptoLookup:

    def detect_type(self, address: str) -> str:
        address = address.strip()
        if re.match(r'^(1|3)[a-zA-Z0-9]{25,34}$', address):
            return "bitcoin"
        if re.match(r'^bc1[a-zA-Z0-9]{6,87}$', address):
            return "bitcoin"
        if re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return "ethereum"
        if re.match(r'^[LM][a-zA-Z0-9]{26,33}$', address):
            return "litecoin"
        return "unknown"

    def _btc_price(self) -> float:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=6,
            )
            if r.status_code == 200:
                return r.json().get("bitcoin", {}).get("usd", 0)
        except Exception:
            pass
        return 0

    def _eth_price(self) -> float:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
                timeout=6,
            )
            if r.status_code == 200:
                return r.json().get("ethereum", {}).get("usd", 0)
        except Exception:
            pass
        return 0

    def lookup_bitcoin(self, address: str) -> Dict[str, Any]:
        result = {
            "address": address,
            "type": "Bitcoin (BTC)",
            "balance": None,
            "balance_usd": None,
            "total_received": None,
            "total_sent": None,
            "tx_count": None,
            "explorer_url": f"https://www.blockchain.com/explorer/addresses/btc/{address}",
            "error": None,
        }
        try:
            r = requests.get(
                f"https://blockchain.info/rawaddr/{address}?limit=0",
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json()
                sat = 1e8
                balance_btc = data.get("final_balance", 0) / sat
                result["balance"] = f"{balance_btc:.8f} BTC"
                result["total_received"] = f"{data.get('total_received', 0) / sat:.8f} BTC"
                result["total_sent"] = f"{data.get('total_sent', 0) / sat:.8f} BTC"
                result["tx_count"] = data.get("n_tx", 0)
                price = self._btc_price()
                if price:
                    result["balance_usd"] = f"${balance_btc * price:,.2f}"
            else:
                result["error"] = f"API returned HTTP {r.status_code}"
        except Exception as e:
            result["error"] = str(e)
        return result

    def lookup_ethereum(self, address: str) -> Dict[str, Any]:
        result = {
            "address": address,
            "type": "Ethereum (ETH)",
            "balance": None,
            "balance_usd": None,
            "total_received": None,
            "total_sent": None,
            "tx_count": None,
            "explorer_url": f"https://etherscan.io/address/{address}",
            "error": None,
        }
        try:
            r = requests.get(
                f"https://api.ethplorer.io/getAddressInfo/{address}?apiKey=freekey",
                timeout=12,
            )
            if r.status_code == 200:
                data = r.json()
                eth = data.get("ETH", {})
                balance_eth = float(eth.get("balance", 0))
                result["balance"] = f"{balance_eth:.6f} ETH"
                result["tx_count"] = eth.get("txCount", None)
                price = self._eth_price()
                if price:
                    result["balance_usd"] = f"${balance_eth * price:,.2f}"
            else:
                result["error"] = f"API returned HTTP {r.status_code}"
        except Exception as e:
            result["error"] = str(e)
        return result

    def lookup(self, address: str) -> Dict[str, Any]:
        address = address.strip()
        crypto_type = self.detect_type(address)
        if crypto_type == "bitcoin":
            return self.lookup_bitcoin(address)
        elif crypto_type == "ethereum":
            return self.lookup_ethereum(address)
        else:
            return {
                "address": address,
                "type": "unknown",
                "error": "Unrecognised address format. Supported: Bitcoin (1…/3…/bc1…), Ethereum (0x…)",
            }
