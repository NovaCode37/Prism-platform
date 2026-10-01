import re
import requests
import time
import threading
from typing import Dict, Any
from modules import get_proxies


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

    _prices_cache = None
    _prices_error = None
    _prices_timestamp = 0.0
    _prices_lock = threading.Lock()

    def _fetch_prices(self) -> None:
        now = time.time()
        if CryptoLookup._prices_cache is not None and (now - CryptoLookup._prices_timestamp < 3600):
            return
        if CryptoLookup._prices_error is not None and (now - CryptoLookup._prices_timestamp < 60):
            return

        with CryptoLookup._prices_lock:
            now = time.time()
            if CryptoLookup._prices_cache is not None and (now - CryptoLookup._prices_timestamp < 3600):
                return
            if CryptoLookup._prices_error is not None and (now - CryptoLookup._prices_timestamp < 60):
                return

            try:
                proxies = get_proxies()
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,litecoin&vs_currencies=usd",
                    timeout=6,
                    proxies=proxies,
                )
                if r.status_code == 200:
                    data = r.json()
                    CryptoLookup._prices_cache = {
                        "bitcoin": data.get("bitcoin", {}).get("usd", 0.0),
                        "ethereum": data.get("ethereum", {}).get("usd", 0.0),
                        "litecoin": data.get("litecoin", {}).get("usd", 0.0),
                    }
                    CryptoLookup._prices_error = None
                elif r.status_code == 429:
                    CryptoLookup._prices_error = "CoinGecko returned 429"
                    CryptoLookup._prices_cache = None
                else:
                    CryptoLookup._prices_error = f"CoinGecko returned {r.status_code}"
                    CryptoLookup._prices_cache = None
            except Exception as e:
                CryptoLookup._prices_error = str(e)
                CryptoLookup._prices_cache = None
            finally:
                CryptoLookup._prices_timestamp = time.time()

    def _get_price(self, coin_id: str) -> float:
        self._fetch_prices()
        if CryptoLookup._prices_cache:
            return CryptoLookup._prices_cache.get(coin_id, 0.0)
        return 0.0

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
            proxies = get_proxies()
            r = requests.get(
                f"https://blockchain.info/rawaddr/{address}?limit=0",
                timeout=12,
                proxies=proxies,
            )
            if r.status_code == 200:
                data = r.json()
                sat = 1e8
                balance_btc = data.get("final_balance", 0) / sat
                result["balance"] = f"{balance_btc:.8f} BTC"
                result["total_received"] = f"{data.get('total_received', 0) / sat:.8f} BTC"
                result["total_sent"] = f"{data.get('total_sent', 0) / sat:.8f} BTC"
                result["tx_count"] = data.get("n_tx", 0)
                price = self._get_price("bitcoin")
                if price:
                    result["balance_usd"] = f"${balance_btc * price:,.2f}"
                elif CryptoLookup._prices_error:
                    result["price_unavailable"] = CryptoLookup._prices_error
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
            proxies = get_proxies()
            r = requests.get(
                f"https://api.ethplorer.io/getAddressInfo/{address}?apiKey=freekey",
                timeout=12,
                proxies=proxies,
            )
            if r.status_code == 200:
                data = r.json()
                eth = data.get("ETH", {})
                balance_eth = float(eth.get("balance", 0))
                result["balance"] = f"{balance_eth:.6f} ETH"
                result["tx_count"] = eth.get("txCount", None)
                price = self._get_price("ethereum")
                if price:
                    result["balance_usd"] = f"${balance_eth * price:,.2f}"
                elif CryptoLookup._prices_error:
                    result["price_unavailable"] = CryptoLookup._prices_error
            else:
                result["error"] = f"API returned HTTP {r.status_code}"
        except Exception as e:
            result["error"] = str(e)
        return result

    def lookup_litecoin(self, address: str) -> Dict[str, Any]:
        result = {
            "address": address,
            "type": "Litecoin (LTC)",
            "balance": None,
            "balance_usd": None,
            "total_received": None,
            "total_sent": None,
            "tx_count": None,
            "explorer_url": f"https://blockchair.com/litecoin/address/{address}",
            "error": None,
        }
        try:
            proxies = get_proxies()
            r = requests.get(
                f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance",
                timeout=12,
                proxies=proxies,
            )
            if r.status_code == 200:
                data = r.json()
                sat = 1e8
                balance_ltc = data.get("final_balance", 0) / sat
                result["balance"] = f"{balance_ltc:.8f} LTC"
                result["total_received"] = f"{data.get('total_received', 0) / sat:.8f} LTC"
                result["total_sent"] = f"{data.get('total_sent', 0) / sat:.8f} LTC"
                result["tx_count"] = data.get("n_tx", 0)
                price = self._get_price("litecoin")
                if price:
                    result["balance_usd"] = f"${balance_ltc * price:,.2f}"
                elif CryptoLookup._prices_error:
                    result["price_unavailable"] = CryptoLookup._prices_error
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
        elif crypto_type == "litecoin":
            return self.lookup_litecoin(address)
        else:
            return {
                "address": address,
                "type": "unknown",
                "error": "Unrecognised address format. Supported: Bitcoin (1.../3.../bc1...), Ethereum (0x...)",
            }
