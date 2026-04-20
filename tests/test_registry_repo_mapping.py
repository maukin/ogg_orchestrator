from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.repositories.registry_repo import RegistryRepository


class DummyLob:
    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


def test_registry_repo_map_row_handles_lobs():
    row = (
        "T1",                    # 0 table_id
        "SRCDB",                 # 1
        "PDB1",                  # 2
        "SRC",                   # 3
        "ORDERS",                # 4
        "TGTDB",                 # 5
        "PDB2",                  # 6
        "DDS",                   # 7
        "ORDERS",                # 8
        "Y",                     # 9 desired_enabled
        ReplicationMode.INITIAL_PLUS_CDC.value,  # 10
        "EXT_01",                # 11
        "REP_01",                # 12
        LoadMethod.DATAPUMP.value,  # 13
        "NORMAL",                # 14
        "MEDIUM",                # 15
        None,                    # 16
        None,                    # 17
        None,                    # 18
        TableState.ACTIVE.value, # 19
        ValidationStatus.PASSED.value,  # 20
        "Y",                     # 21
        123456,                  # 22 registration_scn
        123999,                  # 23 instantiation_candidate_scn
        124000,                  # 24 instantiation_scn
        None,                    # 25
        None,                    # 26
        None,                    # 27
        None,                    # 28
        None,                    # 29
        "dep1",                  # 30
        None,                    # 31
        DummyLob("boom"),        # 32
        None,                    # 33
        None,                    # 34
        DummyLob('["ID"]'),      # 35
        "metadata/orders.json",  # 36
    )

    record = RegistryRepository._map_row(row)

    assert record.table_id == "T1"
    assert record.desired_enabled is True
    assert record.prepared_for_instantiation is True
    assert record.primary_key == ("ID",)
    assert record.last_error_message == "boom"
    assert record.instantiation_candidate_scn == 123999
    assert record.instantiation_scn == 124000