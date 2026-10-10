import hashlib
import os
from web.app import _CACHE_DIR, _cache_key
def test_cache_key_uses_sha256_prefix():
    module = "example_module"
    target = " Example.com "
    expected_hash = hashlib.sha256(
        f"{module}:{target.lower().strip()}".encode()
    ).hexdigest()[:32]

    assert _cache_key(module, target) == os.path.join(
        _CACHE_DIR, f"{module}_{expected_hash}.json"
    )


def test_cache_key_normalizes_target():
    assert _cache_key("example_module", " Example.com ") == _cache_key(
        "example_module", "example.com"
    )
