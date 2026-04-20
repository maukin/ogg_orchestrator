from app.utils.oracle_types import (
    bool_to_char_flag,
    char_flag_to_bool,
    load_json_lob,
    read_lob,
)


class DummyLob:
    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


def test_read_lob_returns_plain_value_as_is():
    assert read_lob("abc") == "abc"


def test_read_lob_reads_lob_object():
    assert read_lob(DummyLob("hello")) == "hello"


def test_char_flag_to_bool():
    assert char_flag_to_bool("Y") is True
    assert char_flag_to_bool("N") is False
    assert char_flag_to_bool(None) is False


def test_bool_to_char_flag():
    assert bool_to_char_flag(True) == "Y"
    assert bool_to_char_flag(False) == "N"


def test_load_json_lob_reads_json_from_lob():
    value = DummyLob('["A", "B"]')
    assert load_json_lob(value, default=[]) == ["A", "B"]


def test_load_json_lob_returns_default_on_none():
    assert load_json_lob(None, default=[]) == []