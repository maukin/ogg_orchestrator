ALTER TABLE etl_deployments ADD error_message CLOB;
ALTER TABLE etl_table_events ADD created_at TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL;