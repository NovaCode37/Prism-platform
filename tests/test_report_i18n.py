from string import Formatter

import pytest

from modules.report_i18n import MESSAGES, get_messages, make_translator


def _placeholders(message: str) -> set[str]:
    return {field for _, field, _, _ in Formatter().parse(message) if field}


def test_every_language_matches_english_contract():
    english = MESSAGES["en"]

    for language, messages in MESSAGES.items():
        missing = english.keys() - messages.keys()
        extra = messages.keys() - english.keys()
        assert not missing, f"{language} is missing: {', '.join(sorted(missing))}"
        assert not extra, f"{language} has extra keys: {', '.join(sorted(extra))}"

        for key, message in messages.items():
            assert _placeholders(message) == _placeholders(english[key]), (
                f"{language}:{key} has different placeholders"
            )


@pytest.mark.parametrize("language", [None, "", "xx"])
def test_get_messages_falls_back_to_english(language):
    assert get_messages(language) is MESSAGES["en"]


@pytest.mark.parametrize("regional, base", [("pt-BR", "pt"), ("zh-CN", "zh")])
def test_get_messages_uses_base_language(regional, base):
    assert get_messages(regional) is MESSAGES[base]


def test_translator_substitutes_and_falls_back(monkeypatch):
    assert make_translator("de")("opsec.risk", level="HIGH") == "HIGH RISIKO"

    monkeypatch.delitem(MESSAGES["de"], "opsec.risk")
    assert make_translator("de")("opsec.risk", level="HIGH") == "HIGH RISK"
    assert make_translator("de")("missing.key") == "missing.key"
