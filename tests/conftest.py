import pytest
from retro_rus_plugin import ChadTranslator


@pytest.fixture
def fake_dict():
    return {
        "мир": "мiръ",
        "привет": "прiветъ",
        "дом": "домъ",
    }

@pytest.fixture
def plugin():
    return ChadTranslator()


@pytest.fixture
def fake_params():
    class P:
        message = ""
    return P()
