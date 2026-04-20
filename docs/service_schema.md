# Service schema

The orchestrator requires the following Oracle service objects:

- `ETL_DEPLOYMENTS`
- `ETL_TABLE_REGISTRY`
- `ETL_TABLE_EVENTS`
- `SEQ_ETL_TABLE_EVENTS`

## Bootstrap

Use:

- `sql/bootstrap_service_schema.sql`

for fresh installation.

## Upgrade

Use:

- `sql/upgrade_service_schema.sql`

for existing installations that were created before the latest schema contract.

## Notes

### ETL_DEPLOYMENTS
Stores deployment-level metadata:
- plan
- lifecycle status
- timestamps
- top-level error message

### ETL_TABLE_REGISTRY
Stores current table orchestration state:
- desired state
- actual state
- validation status
- SCN metadata
- timestamps
- error details

### ETL_TABLE_EVENTS
Stores append-only table-level event history.

### Oracle-specific conventions
- boolean flags are stored as `CHAR(1)` with values `Y` / `N`
- JSON payloads are stored in `CLOB`
- SCN values are stored in `NUMBER(20)`