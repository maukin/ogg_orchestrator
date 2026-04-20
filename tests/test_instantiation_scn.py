import pytest

from app.utils.instantiation_scn import resolve_instantiation_scn


def test_resolve_instantiation_scn_prefers_candidate():
    assert resolve_instantiation_scn(100, 200) == 200


def test_resolve_instantiation_scn_falls_back_to_registration():
    assert resolve_instantiation_scn(100, None) == 100


def test_resolve_instantiation_scn_raises_when_both_missing():
    with pytest.raises(ValueError):
        resolve_instantiation_scn(None, None)