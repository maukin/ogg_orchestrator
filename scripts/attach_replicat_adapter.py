from __future__ import annotations

import json
import os
import re
import shutil
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


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [str(line).rstrip() for line in lines if str(line).strip()]
    text = "\n".join(normalized).strip()
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def get_auth() -> tuple[str, str]:
    return require_env("OGG_REST_USERNAME"), require_env("OGG_REST_PASSWORD")


def get_base_url() -> str:
    return require_env("OGG_REST_BASE_URL").rstrip("/")


def normalize_fragment_lines(fragment_text: str) -> list[str]:
    return [line.strip() for line in fragment_text.splitlines() if line.strip()]


def fetch_replicat(replicat_name: str) -> dict:
    url = f"{get_base_url()}/services/v2/replicats/{replicat_name}"
    response = requests.get(
        url,
        auth=get_auth(),
        verify=False,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def patch_replicat(replicat_name: str, payload: dict) -> requests.Response:
    url = f"{get_base_url()}/services/v2/replicats/{replicat_name}"
    return requests.patch(
        url,
        auth=get_auth(),
        json=payload,
        verify=False,
        timeout=30,
    )


def post_replicat_command(replicat_name: str, command: str) -> requests.Response:
    url = f"{get_base_url()}/services/v2/replicats/{replicat_name}/command"
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


def restart_replicat(replicat_name: str, artifacts_dir: Path) -> tuple[bool, str]:
    stop_resp = post_replicat_command(replicat_name, "STOP")
    stop_payload = {
        "http_status": stop_resp.status_code,
        "response_text": stop_resp.text,
    }
    write_json(artifacts_dir / "attach_replicat_stop_response.json", stop_payload)

    stop_text_upper = (stop_resp.text or "").upper()
    stop_ok = 200 <= stop_resp.status_code < 300
    stop_not_running = "NOT CURRENTLY RUNNING" in stop_text_upper

    if not stop_ok:
        return False, f"STOP failed: {stop_resp.status_code} {stop_resp.text}"

    resume_resp = post_replicat_command(replicat_name, "RESUME")
    resume_payload = {
        "http_status": resume_resp.status_code,
        "response_text": resume_resp.text,
    }
    write_json(artifacts_dir / "attach_replicat_resume_response.json", resume_payload)

    if not (200 <= resume_resp.status_code < 300):
        return False, f"RESUME failed: {resume_resp.status_code} {resume_resp.text}"

    return True, (
        "Restart completed successfully."
        if not stop_not_running
        else "Replicat was not running; resume command submitted successfully."
    )


def copy_fragment_to_generated(fragment_path: Path, generated_dir: Path) -> Path:
    generated_dir.mkdir(parents=True, exist_ok=True)
    target_path = generated_dir / fragment_path.name

    if fragment_path.resolve() != target_path.resolve():
        shutil.copy2(fragment_path, target_path)

    return target_path


def _extract_map_key(line: str) -> tuple[str, str] | None:
    """
    Returns:
        (source_schema.table, target_schema.table)
    for lines like:
        MAP SRC.T1, TARGET TGT.T1;
        MAP SRC.T1, TARGET TGT.T1, FILTER (...);
    """
    pattern = re.compile(
        r"^\s*MAP\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+)\s*,\s*TARGET\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+)",
        re.IGNORECASE,
    )
    match = pattern.match(line.strip())
    if not match:
        return None
    return match.group(1).upper(), match.group(2).upper()


def _replace_replicat_map_lines(
    current_cfg: list[str],
    fragment_lines: list[str],
) -> tuple[list[str], int, bool]:
    """
    Replaces existing MAP entries for the same source/target with the fragment lines.
    Returns:
        (new_config, applied_count, changed)
    """
    fragment_keys: dict[tuple[str, str], str] = {}

    for line in fragment_lines:
        key = _extract_map_key(line)
        if key is None:
            raise RuntimeError(f"Unsupported replicat fragment line, expected MAP ... TARGET ...: {line}")
        fragment_keys[key] = line

    new_cfg: list[str] = []
    replaced_keys: set[tuple[str, str]] = set()
    changed = False

    for line in current_cfg:
        key = _extract_map_key(line)
        if key is not None and key in fragment_keys:
            if key not in replaced_keys:
                new_line = fragment_keys[key]
                new_cfg.append(new_line)
                replaced_keys.add(key)
                if line.strip() != new_line.strip():
                    changed = True
            else:
                changed = True
            continue

        new_cfg.append(line)

    for key, line in fragment_keys.items():
        if key not in replaced_keys:
            new_cfg.append(line)
            replaced_keys.add(key)
            changed = True

    applied_count = len(fragment_lines)
    return new_cfg, applied_count, changed


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/attach_replicat_adapter.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])
    artifacts_dir = response_path.parent

    cdc_replicat_dir = artifacts_dir / "cdc" / "replicat"
    generated_dir = cdc_replicat_dir / "generated"
    backup_dir = cdc_replicat_dir / "backup"
    before_dir = cdc_replicat_dir / "effective_before"
    after_dir = cdc_replicat_dir / "effective_after"

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
                "raw_output": "No attach_replicat commands.",
                "error_code": None,
                "error_message": None,
                "restart_performed": False,
                "rollback_performed": False,
            },
        )
        return 0

    try:
        group_name = commands[0]["replicat_group"]

        before_doc = fetch_replicat(group_name)
        write_json(
            backup_dir / f"{group_name}_{timestamp_for_file()}_backup.json",
            before_doc,
        )
        write_json(artifacts_dir / "attach_replicat_before.json", before_doc)

        before_cfg = list(before_doc.get("response", {}).get("config", []))
        if not before_cfg:
            raise RuntimeError(f"Replicat {group_name} returned empty config.")

        write_lines(before_dir / f"{group_name}.prm", before_cfg)
        write_json(before_dir / f"{group_name}.json", before_doc)

        current_cfg = list(before_cfg)
        total_applied = 0
        changed = False

        for cmd in commands:
            fragment_path = Path(cmd["fragment_path"])
            if not fragment_path.exists():
                raise RuntimeError(f"Replicat fragment file not found: {fragment_path}")

            generated_fragment_path = copy_fragment_to_generated(fragment_path, generated_dir)

            fragment_lines = normalize_fragment_lines(read_text(generated_fragment_path))
            if not fragment_lines:
                raise RuntimeError(f"Replicat fragment is empty: {generated_fragment_path}")

            current_cfg, applied_count, this_changed = _replace_replicat_map_lines(
                current_cfg=current_cfg,
                fragment_lines=fragment_lines,
            )
            total_applied += applied_count
            changed = changed or this_changed

        if not changed:
            write_lines(after_dir / f"{group_name}.prm", current_cfg)
            write_json(
                after_dir / f"{group_name}.json",
                {
                    "group_name": group_name,
                    "config": current_cfg,
                    "note": "No changes applied; effective_after equals effective_before.",
                },
            )

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
                    "raw_output": "All replicat rules already present in the desired form. No changes applied.",
                    "error_code": None,
                    "error_message": None,
                    "restart_performed": False,
                    "rollback_performed": False,
                },
            )
            return 0

        patch_payload = {"config": current_cfg}
        write_json(artifacts_dir / "attach_replicat_patch_payload.json", patch_payload)

        patch_resp = patch_replicat(group_name, patch_payload)
        write_json(
            artifacts_dir / "attach_replicat_patch_response.json",
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
                    "error_message": f"Replicat PATCH failed: {patch_resp.status_code}",
                    "restart_performed": False,
                    "rollback_performed": False,
                },
            )
            return 1

        restart_ok, restart_msg = restart_replicat(group_name, artifacts_dir)
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

        after_doc = fetch_replicat(group_name)
        write_json(artifacts_dir / "attach_replicat_after.json", after_doc)

        after_cfg = list(after_doc.get("response", {}).get("config", []))
        write_lines(after_dir / f"{group_name}.prm", after_cfg)
        write_json(after_dir / f"{group_name}.json", after_doc)

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
                "group_name": commands[0].get("replicat_group") if commands else None,
                "applied_tables_count": None,
                "started_at": started_at,
                "finished_at": utc_now(),
                "raw_output": None,
                "error_code": "ATTACH_REPLICAT_EXCEPTION",
                "error_message": str(exc),
                "restart_performed": False,
                "rollback_performed": False,
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())