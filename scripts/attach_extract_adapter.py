from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_for_file() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_auth() -> tuple[str, str]:
    return require_env("OGG_REST_USERNAME"), require_env("OGG_REST_PASSWORD")


def get_base_url() -> str:
    return require_env("OGG_REST_BASE_URL").rstrip("/")


def normalize_fragment_lines(fragment_text: str) -> list[str]:
    return [line.strip() for line in fragment_text.splitlines() if line.strip()]


def fetch_extract(extract_name: str) -> dict:
    url = f"{get_base_url()}/services/v2/extracts/{extract_name}"
    response = requests.get(
        url,
        auth=get_auth(),
        verify=False,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def patch_extract(extract_name: str, payload: dict) -> requests.Response:
    url = f"{get_base_url()}/services/v2/extracts/{extract_name}"
    return requests.patch(
        url,
        auth=get_auth(),
        json=payload,
        verify=False,
        timeout=30,
    )


def post_extract_command(extract_name: str, command: str) -> requests.Response:
    url = f"{get_base_url()}/services/v2/extracts/{extract_name}/command"
    payload = {
        "$schema": "er:command",
        "command": command.upper(),
    }
    return requests.post(
        url,
        auth=get_auth(),
        json=payload,
        verify=False,
        timeout=30,
    )


def restart_extract(extract_name: str, artifacts_dir: Path) -> tuple[bool, str]:
    stop_resp = post_extract_command(extract_name, "STOP")
    stop_payload = {
        "http_status": stop_resp.status_code,
        "response_text": stop_resp.text,
    }
    write_json(artifacts_dir / "attach_extract_stop_response.json", stop_payload)

    stop_text_upper = (stop_resp.text or "").upper()
    stop_ok = 200 <= stop_resp.status_code < 300
    stop_not_running = "NOT CURRENTLY RUNNING" in stop_text_upper

    if not stop_ok:
        return False, f"STOP failed: {stop_resp.status_code} {stop_resp.text}"

    resume_resp = post_extract_command(extract_name, "RESUME")
    resume_payload = {
        "http_status": resume_resp.status_code,
        "response_text": resume_resp.text,
    }
    write_json(artifacts_dir / "attach_extract_resume_response.json", resume_payload)

    if not (200 <= resume_resp.status_code < 300):
        return False, f"RESUME failed: {resume_resp.status_code} {resume_resp.text}"

    return True, (
        "Restart completed successfully."
        if not stop_not_running
        else "Extract was not running; resume command submitted successfully."
    )


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/attach_extract_adapter.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])
    artifacts_dir = response_path.parent
    backup_dir = artifacts_dir / "cdc" / "extract"

    request_payload = json.loads(read_text(request_path))
    commands = request_payload.get("commands", [])
    started_at = utc_now()

    if not commands:
        write_json(
            response_path,
            {
                "success": True,
                "executed_count": 0,
                "skipped_count": 0,
                "group_name": None,
                "applied_tables_count": 0,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": "No attach_extract commands.",
                "error_code": None,
                "error_message": None,
                "restart_performed": False,
                "rollback_performed": False,
            },
        )
        return 0

    try:
        group_name = commands[0]["extract_group"]

        before_doc = fetch_extract(group_name)
        write_json(
            backup_dir / f"{group_name}_{timestamp_for_file()}_backup.json",
            before_doc,
        )
        write_json(artifacts_dir / "attach_extract_before.json", before_doc)

        before_cfg = list(before_doc.get("response", {}).get("config", []))
        if not before_cfg:
            raise RuntimeError(f"Extract {group_name} returned empty config.")

        current_cfg = list(before_cfg)
        current_set = {line.strip() for line in current_cfg if str(line).strip()}

        total_applied = 0
        changed = False

        for cmd in commands:
            fragment_path = Path(cmd["fragment_path"])
            if not fragment_path.exists():
                raise RuntimeError(f"Extract fragment file not found: {fragment_path}")

            fragment_lines = normalize_fragment_lines(read_text(fragment_path))
            if not fragment_lines:
                raise RuntimeError(f"Extract fragment is empty: {fragment_path}")

            for line in fragment_lines:
                if line not in current_set:
                    current_cfg.append(line)
                    current_set.add(line)
                    changed = True
                    total_applied += 1

        if not changed:
            write_json(
                response_path,
                {
                    "success": True,
                    "executed_count": 0,
                    "skipped_count": len(commands),
                    "group_name": group_name,
                    "applied_tables_count": 0,
                    "started_at": started_at,
                    "finished_at": utc_now(),
                    "raw_output": "All extract rules already present. No changes applied.",
                    "error_code": None,
                    "error_message": None,
                    "restart_performed": False,
                    "rollback_performed": False,
                },
            )
            return 0

        patch_payload = {"config": current_cfg}
        write_json(artifacts_dir / "attach_extract_patch_payload.json", patch_payload)

        patch_resp = patch_extract(group_name, patch_payload)
        write_json(
            artifacts_dir / "attach_extract_patch_response.json",
            {"http_status": patch_resp.status_code, "response_text": patch_resp.text},
        )

        if not (200 <= patch_resp.status_code < 300):
            write_json(
                response_path,
                {
                    "success": False,
                    "executed_count": 0,
                    "skipped_count": 0,
                    "group_name": group_name,
                    "applied_tables_count": total_applied,
                    "started_at": started_at,
                    "finished_at": utc_now(),
                    "raw_output": patch_resp.text,
                    "error_code": f"PATCH_HTTP_{patch_resp.status_code}",
                    "error_message": f"Extract PATCH failed: {patch_resp.status_code}",
                    "restart_performed": False,
                    "rollback_performed": False,
                },
            )
            return 1

        restart_ok, restart_msg = restart_extract(group_name, artifacts_dir)
        if not restart_ok:
            write_json(
                response_path,
                {
                    "success": False,
                    "executed_count": 0,
                    "skipped_count": 0,
                    "group_name": group_name,
                    "applied_tables_count": total_applied,
                    "started_at": started_at,
                    "finished_at": utc_now(),
                    "raw_output": restart_msg,
                    "error_code": "RESTART_FAILED",
                    "error_message": restart_msg,
                    "restart_performed": True,
                    "rollback_performed": False,
                },
            )
            return 1

        after_doc = fetch_extract(group_name)
        write_json(artifacts_dir / "attach_extract_after.json", after_doc)

        write_json(
            response_path,
            {
                "success": True,
                "executed_count": len(commands),
                "skipped_count": 0,
                "group_name": group_name,
                "applied_tables_count": total_applied,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": restart_msg,
                "error_code": None,
                "error_message": None,
                "restart_performed": True,
                "rollback_performed": False,
            },
        )
        return 0

    except Exception as exc:
        write_json(
            response_path,
            {
                "success": False,
                "executed_count": 0,
                "skipped_count": 0,
                "group_name": commands[0].get("extract_group") if commands else None,
                "applied_tables_count": None,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": None,
                "error_code": "ATTACH_EXTRACT_EXCEPTION",
                "error_message": str(exc),
                "restart_performed": False,
                "rollback_performed": False,
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())