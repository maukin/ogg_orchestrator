CREATE TABLE etl_deployments (
    deployment_id        VARCHAR2(128)   NOT NULL,
    environment_name     VARCHAR2(50)    NOT NULL,
    git_branch           VARCHAR2(255),
    git_commit_sha       VARCHAR2(100),
    pipeline_id          VARCHAR2(100),
    trigger_source       VARCHAR2(100),
    status               VARCHAR2(30)    NOT NULL,
    plan_json            CLOB,
    rollback_plan_json   CLOB,
    started_at           TIMESTAMP(6)    NOT NULL,
    finished_at          TIMESTAMP(6),
    initiated_by         VARCHAR2(128),
    created_at           TIMESTAMP(6)    NOT NULL,
    error_message        CLOB,
    CONSTRAINT pk_etl_deployments PRIMARY KEY (deployment_id)
);

CREATE TABLE etl_table_registry (
    table_id                     VARCHAR2(300)   NOT NULL,
    source_system                VARCHAR2(100)   NOT NULL,
    source_pdb                   VARCHAR2(128),
    source_schema                VARCHAR2(128)   NOT NULL,
    source_table                 VARCHAR2(128)   NOT NULL,
    target_system                VARCHAR2(100)   NOT NULL,
    target_pdb                   VARCHAR2(128),
    target_schema                VARCHAR2(128)   NOT NULL,
    target_table                 VARCHAR2(128)   NOT NULL,
    desired_enabled              CHAR(1)         NOT NULL,
    desired_replication_mode     VARCHAR2(30)    NOT NULL,
    desired_cdc_group            VARCHAR2(128),
    desired_load_method          VARCHAR2(30),
    desired_priority             VARCHAR2(30),
    desired_size_class           VARCHAR2(30),
    actual_extract_group         VARCHAR2(128),
    actual_replicat_group        VARCHAR2(128),
    actual_load_batch_id         VARCHAR2(128),
    state                        VARCHAR2(50)    NOT NULL,
    validation_status            VARCHAR2(30)    NOT NULL,
    prepared_for_instantiation   CHAR(1)         NOT NULL,
    registration_scn             NUMBER(20),
	instantiation_candidate_scn  NUMBER(20),
    instantiation_scn            NUMBER(20),
    initial_load_started_at      TIMESTAMP(6),
    initial_load_finished_at     TIMESTAMP(6),
    cdc_capture_attached_at      TIMESTAMP(6),
    cdc_apply_attached_at        TIMESTAMP(6),
    activated_at                 TIMESTAMP(6),
    last_deployment_id           VARCHAR2(128),
    last_error_code              VARCHAR2(100),
    last_error_message           CLOB,
    created_at                   TIMESTAMP(6)    NOT NULL,
    updated_at                   TIMESTAMP(6)    NOT NULL,
    primary_key_json             CLOB,
    metadata_file                VARCHAR2(1000),
    desired_extract_group        VARCHAR2(128),
    desired_replicat_group       VARCHAR2(128),
    CONSTRAINT pk_etl_table_registry PRIMARY KEY (table_id),
    CONSTRAINT chk_etl_reg_enabled CHECK (desired_enabled IN ('Y', 'N')),
    CONSTRAINT chk_etl_reg_prepared CHECK (prepared_for_instantiation IN ('Y', 'N'))
);

CREATE TABLE etl_table_events (
    event_id          NUMBER(20)      NOT NULL,
    table_id          VARCHAR2(300)   NOT NULL,
    deployment_id     VARCHAR2(128),
    event_type        VARCHAR2(50)    NOT NULL,
    event_status      VARCHAR2(30)    NOT NULL,
    step_name         VARCHAR2(100),
    event_ts          TIMESTAMP(6),
    payload_json      CLOB,
    error_code        VARCHAR2(100),
    error_message     CLOB,
    created_by        VARCHAR2(128),
    created_at        TIMESTAMP(6)    DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_etl_table_events PRIMARY KEY (event_id)
);

CREATE SEQUENCE seq_etl_table_events
    START WITH 1
    INCREMENT BY 1
    NOCACHE;

CREATE INDEX idx_etl_reg_state
    ON etl_table_registry (state);

CREATE INDEX idx_etl_reg_last_dep
    ON etl_table_registry (last_deployment_id);

CREATE INDEX idx_etl_evt_table_id
    ON etl_table_events (table_id);

CREATE INDEX idx_etl_evt_dep_id
    ON etl_table_events (deployment_id);

CREATE INDEX idx_etl_evt_type
    ON etl_table_events (event_type);

CREATE INDEX idx_etl_dep_status
    ON etl_deployments (status);