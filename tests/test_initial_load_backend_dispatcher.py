from app.integrations.initial_load_backends import InitialLoadBackendDispatcher


def test_initial_load_backend_dispatcher_maps_datapump(monkeypatch):
    monkeypatch.setenv("SOURCE_DB_CONNECT_STRING", "src_conn")
    monkeypatch.setenv("TARGET_DB_CONNECT_STRING", "tgt_conn")
    monkeypatch.setenv("DATAPUMP_NETWORK_LINK", "source_link")
    monkeypatch.setenv("DATAPUMP_DIRECTORY", "DATA_PUMP_DIR")
    monkeypatch.setenv("INITIAL_LOAD_REQUIRE_EMPTY_TARGET", "true")
    monkeypatch.setenv("DATAPUMP_DEFAULT_PARALLEL", "1")

    dispatcher = InitialLoadBackendDispatcher()
    backend = dispatcher.get_backend("DATAPUMP")

    assert backend.__class__.__name__ == "DataPumpBackend"


def test_initial_load_backend_dispatcher_maps_unsupported_parallel():
    dispatcher = InitialLoadBackendDispatcher()
    backend = dispatcher.get_backend("OGG_INITIAL_PARALLEL")

    assert backend.__class__.__name__ == "UnsupportedBackend"