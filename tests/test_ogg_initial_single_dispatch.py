from app.integrations.initial_load_backends import InitialLoadBackendDispatcher


def test_initial_load_backend_dispatcher_maps_ogg_single(monkeypatch):
    monkeypatch.setenv("SOURCE_DB_CONNECT_STRING", "src_conn")
    monkeypatch.setenv("TARGET_DB_CONNECT_STRING", "tgt_conn")
    monkeypatch.setenv("OGG_ADMIN_URL", "http://ogg-host:9010")
    monkeypatch.setenv("OGG_ADMIN_DEPLOYMENT", "GG-01")
    monkeypatch.setenv("OGG_ADMIN_USER", "ggadmin")
    monkeypatch.setenv("OGG_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("OGG_PARAM_DIR", ".")
    monkeypatch.setenv("OGG_TEMP_DIR", ".")
    monkeypatch.setenv("OGG_SOURCE_USERID", "src_user")
    monkeypatch.setenv("OGG_SOURCE_PASSWORD", "src_pwd")
    monkeypatch.setenv("OGG_TARGET_USERID", "tgt_user")
    monkeypatch.setenv("OGG_TARGET_PASSWORD", "tgt_pwd")
    monkeypatch.setenv("OGG_ADMINCLIENT_PATH", "adminclient")

    monkeypatch.setattr(
        "app.integrations.initial_load_backends._resolve_tool_path",
        lambda value: value,
    )
    monkeypatch.setattr(
        "app.integrations.initial_load_backends._require_executable",
        lambda value: value,
    )

    dispatcher = InitialLoadBackendDispatcher()
    backend = dispatcher.get_backend("OGG_INITIAL_SINGLE")

    assert backend.__class__.__name__ == "OGGInitialSingleBackend"