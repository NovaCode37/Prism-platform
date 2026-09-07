# tests/test_cli_target_type_detection.py
import pytest
import cli


class TestDetectType:
    """Tests for cli.detect_type target type auto-detection."""

    @pytest.mark.parametrize(
        ("target", "expected_type"),
        [
            # Email detection
            ("user@example.com", "email"),
            ("john.doe+spam@gmail.com", "email"),
            ("admin@company.co.uk", "email"),
            ("user-name@sub.domain.com", "email"),
            ("UPPER@Example.COM", "email"),
            ("test@localhost", "email"),
            
            # Phone number detection
            ("+1 555 000 0000", "phone"),
            ("+79001234567", "phone"),
            ("+44 20 7946 0958", "phone"),
            ("1-555-000-0000", "phone"),
            ("+1 (555) 000-0000", "phone"),
            ("+1234567890", "phone"),
            ("+49 30 1234567", "phone"),
            
            # IP address detection
            ("8.8.8.8", "ip"),
            ("192.168.1.1", "ip"),
            ("10.0.0.1", "ip"),
            ("255.255.255.255", "ip"),
            ("127.0.0.1", "ip"),
            ("1.2.3.4", "ip"),
            
            # Domain detection
            ("example.com", "domain"),
            ("sub.domain.com", "domain"),
            ("my-site.co.uk", "domain"),
            ("example.org", "domain"),
            ("something.io", "domain"),
            ("test.example.com", "domain"),
            ("example.net", "domain"),
            
            # Username detection
            ("@someuser", "username"),
            ("@john_doe", "username"),
            ("@user123", "username"),
            ("@user.name", "username"),
            ("@some_user", "username"),
            
            # Telegram handle detection
            ("t.me/someuser", "telegram"),
            ("telegram.me/someuser", "telegram"),
            ("t.me/user123", "telegram"),
            ("telegram.me/username", "telegram"),
            
            # Username detection (no @ prefix, no domain)
            ("johndoe", "username"),
            ("john_doe", "username"),
            ("user123", "username"),
            ("some_username", "username"),
        ],
    )
    def test_detect_type_various_targets(self, target, expected_type):
        """detect_type should correctly identify target types."""
        assert cli.detect_type(target) == expected_type

    def test_detect_type_phone_with_country_code_strips_characters(self):
        """Phone numbers with various formats should be detected."""
        # Phone numbers with spaces, dashes, parentheses
        assert cli.detect_type("+1 555 000 0000") == "phone"
        assert cli.detect_type("1-555-000-0000") == "phone"
        assert cli.detect_type("+1 (555) 000-0000") == "phone"
        assert cli.detect_type("+44 20 7946 0958") == "phone"
        assert cli.detect_type("+49 30 1234567") == "phone"
        assert cli.detect_type("+79001234567") == "phone"

    def test_detect_type_email_case_insensitive(self):
        """detect_type should handle uppercase email addresses."""
        assert cli.detect_type("User@Example.COM") == "email"
        assert cli.detect_type("USER@EXAMPLE.COM") == "email"

    def test_detect_type_domain_without_subdomain(self):
        """Domains without subdomains should be detected."""
        assert cli.detect_type("example.com") == "domain"
        assert cli.detect_type("example.co.uk") == "domain"
        assert cli.detect_type("example.io") == "domain"

    def test_detect_type_ip_with_dot_separated_digits(self):
        """IP addresses with 4 dot-separated digits should be detected."""
        assert cli.detect_type("1.1.1.1") == "ip"
        assert cli.detect_type("0.0.0.0") == "ip"
        assert cli.detect_type("255.255.255.255") == "ip"

    def test_detect_type_username_uses_domain_pattern(self):
        """Usernames that look like domains should be detected as username."""
        # Without @ prefix, single word with no dot -> username
        assert cli.detect_type("username") == "username"
        assert cli.detect_type("user123") == "username"
        
        # With @ prefix -> username
        assert cli.detect_type("@username") == "username"
        assert cli.detect_type("@user123") == "username"

    def test_detect_type_telegram_handle(self):
        """Telegram handles should be detected."""
        assert cli.detect_type("t.me/someuser") == "telegram"
        assert cli.detect_type("telegram.me/someuser") == "telegram"
        assert cli.detect_type("t.me/username") == "telegram"
        assert cli.detect_type("telegram.me/username") == "telegram"

    def test_detect_type_empty_string(self):
        """Empty string should be detected as username (default fallback)."""
        assert cli.detect_type("") == "username"

    def test_detect_type_username_with_special_characters(self):
        """Usernames with special characters should be detected."""
        assert cli.detect_type("@user-name") == "username"
        assert cli.detect_type("@user_name") == "username"
        assert cli.detect_type("@user.name") == "username"
        assert cli.detect_type("user-name") == "username"
        assert cli.detect_type("user_name") == "username"