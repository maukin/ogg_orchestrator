# Test pilot checklist

## Goal
Run one simple table through:
- prepare source
- initial load
- instantiation
- attach replicat
- activation
- CDC verification

## Recommended pilot table
Choose one table that is:
- small
- has a stable primary key
- has no LOB columns
- has no unusual triggers
- has low write rate
- has simple source-to-target mapping

## Metadata checks
Ensure:
- `desired_enabled = true`
- `desired_replication_mode = INITIAL_PLUS_CDC`
- `desired_extract_group` is valid
- `desired_replicat_group` is valid
- `primary_key` is correct

## Before run
- Service schema validation passes
- Desired state snapshot is up to date
- OGG groups exist
- Source DB prerequisites are already enabled
- Pilot profile env values are filled in

## Run outputs to inspect
- `artifacts/schema_validation_report.json`
- `artifacts/deployment_status_report.json`
- `artifacts/deployment_execution_summary.json`
- `artifacts/deployment_reconciliation_report.json`
- `artifacts/cdc/extract/*.prm`
- `artifacts/cdc/replicat/*.prm`
- `artifacts/initial_load_request.json`
- `artifacts/initial_load_response.json`

## Validation after initial load
- Source row count equals target row count
- 3–5 random rows match
- PK uniqueness is preserved

## Validation after CDC
Perform on source:
- one INSERT
- one UPDATE
- one DELETE

Then verify on target:
- inserted row appears
- updated values are propagated
- deleted row is removed or marked according to target semantics

## Registry checks
Verify:
- table reaches expected lifecycle state
- no unexpected ERROR state
- SCN-related fields are populated as expected
- timestamps are filled in

## Event checks
Verify:
- STARTED/DONE events are present
- no unexpected ERROR_OCCURRED events
- payload contains executor/probe details