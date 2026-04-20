# Initial load adapter contract

## Purpose
The orchestrator calls an external adapter script using:

- request JSON path
- response JSON path

The adapter is responsible for:
1. reading the orchestrator request
2. calling the real initial load implementation
3. translating the result into orchestrator response format

## Command shape

Example:
```bash
python scripts/initial_load_adapter_template.py <request.json> <response.json>