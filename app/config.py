from dataclasses import dataclass
import os


_ALLOWED_ACTIONS = {"SKIP", "PLAN_ONLY", "APPLY"}

_ALLOWED_PREPARE_SOURCE_EXECUTORS = {
    "DRY_RUN",
    "FILE_ONLY",
    "OGG_REST_SKELETON",
    "OGG_REST_REAL",
}
_ALLOWED_ATTACH_EXTRACT_EXECUTORS = {
    "DRY_RUN",
    "FILE_ONLY",
    "SCRIPT",
}
_ALLOWED_INITIAL_LOAD_EXECUTORS = {
    "DRY_RUN",
    "FILE_ONLY",
    "SCRIPT",
}
_ALLOWED_INSTANTIATION_EXECUTORS = {
    "DRY_RUN",
    "FILE_ONLY",
    "SCRIPT",
}
_ALLOWED_ATTACH_REPLICAT_EXECUTORS = {
    "DRY_RUN",
    "FILE_ONLY",
    "SCRIPT",
}


def _get_bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


@dataclass(frozen=True)
class AppConfig:
    oracle_user: str
    oracle_password: str
    oracle_dsn: str

    environment_name: str
    build_desired_state_from_metadata: bool
    metadata_dir: str
    desired_state_path: str

    git_branch: str | None
    git_commit_sha: str | None
    pipeline_id: str | None

    prepare_source_action: str
    prepare_source_executor: str

    attach_extract_action: str
    attach_extract_executor: str

    initial_load_action: str
    initial_load_executor: str

    instantiation_action: str
    instantiation_executor: str

    attach_replicat_action: str
    attach_replicat_executor: str

    activation_action: str

    ogg_rest_base_url: str
    ogg_rest_username: str
    ogg_rest_password: str
    ogg_rest_deployment_name: str
    ogg_rest_verify_ssl: bool
    ogg_rest_mode: str
    allow_real_prepare_source: bool
    ogg_rest_connection: str
    trandata_scope: str

    initial_load_script_timeout_sec: int
    initial_load_script_command: str

    instantiation_script_command: str
    instantiation_script_timeout_sec: int

    attach_extract_script_command: str
    attach_extract_script_timeout_sec: int

    attach_replicat_script_command: str
    attach_replicat_script_timeout_sec: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            oracle_user=os.getenv("ORACLE_USER", ""),
            oracle_password=os.getenv("ORACLE_PASSWORD", ""),
            oracle_dsn=os.getenv("ORACLE_DSN", ""),

            environment_name=os.getenv("ENVIRONMENT_NAME", "dev"),
            build_desired_state_from_metadata=_get_bool_env(
                "BUILD_DESIRED_STATE_FROM_METADATA", "false"
            ),
            metadata_dir=os.getenv("METADATA_DIR", "metadata"),
            desired_state_path=os.getenv("DESIRED_STATE_PATH", "registry/desired_state.json"),

            git_branch=os.getenv("CI_COMMIT_REF_NAME"),
            git_commit_sha=os.getenv("CI_COMMIT_SHA"),
            pipeline_id=os.getenv("CI_PIPELINE_ID"),

            prepare_source_action=os.getenv("PREPARE_SOURCE_ACTION", "PLAN_ONLY").upper(),
            prepare_source_executor=os.getenv("PREPARE_SOURCE_EXECUTOR", "DRY_RUN").upper(),

            attach_extract_action=os.getenv("ATTACH_EXTRACT_ACTION", "PLAN_ONLY").upper(),
            attach_extract_executor=os.getenv("ATTACH_EXTRACT_EXECUTOR", "DRY_RUN").upper(),

            initial_load_action=os.getenv("INITIAL_LOAD_ACTION", "PLAN_ONLY").upper(),
            initial_load_executor=os.getenv("INITIAL_LOAD_EXECUTOR", "DRY_RUN").upper(),

            instantiation_action=os.getenv("INSTANTIATION_ACTION", "PLAN_ONLY").upper(),
            instantiation_executor=os.getenv("INSTANTIATION_EXECUTOR", "DRY_RUN").upper(),

            attach_replicat_action=os.getenv("ATTACH_REPLICAT_ACTION", "PLAN_ONLY").upper(),
            attach_replicat_executor=os.getenv("ATTACH_REPLICAT_EXECUTOR", "DRY_RUN").upper(),

            activation_action=os.getenv("ACTIVATION_ACTION", "PLAN_ONLY").upper(),

            ogg_rest_base_url=os.getenv("OGG_REST_BASE_URL", ""),
            ogg_rest_username=os.getenv("OGG_REST_USERNAME", ""),
            ogg_rest_password=os.getenv("OGG_REST_PASSWORD", ""),
            ogg_rest_deployment_name=os.getenv("OGG_REST_DEPLOYMENT_NAME", ""),
            ogg_rest_verify_ssl=_get_bool_env("OGG_REST_VERIFY_SSL", "true"),
            ogg_rest_mode=os.getenv("OGG_REST_MODE", "OGG_REST_SKELETON").upper(),
            allow_real_prepare_source=_get_bool_env("ALLOW_REAL_PREPARE_SOURCE", "false"),
            ogg_rest_connection=os.getenv("OGG_REST_CONNECTION", ""),
            trandata_scope=os.getenv("TRANDATA_SCOPE", "TABLE").upper(),

            initial_load_script_timeout_sec=int(
                os.getenv("INITIAL_LOAD_SCRIPT_TIMEOUT_SEC", "3600")
            ),
            initial_load_script_command=os.getenv("INITIAL_LOAD_SCRIPT_COMMAND", ""),

            instantiation_script_command=os.getenv("INSTANTIATION_SCRIPT_COMMAND", ""),
            instantiation_script_timeout_sec=int(
                os.getenv("INSTANTIATION_SCRIPT_TIMEOUT_SEC", "1800")
            ),

            attach_extract_script_command=os.getenv("ATTACH_EXTRACT_SCRIPT_COMMAND", ""),
            attach_extract_script_timeout_sec=int(
                os.getenv("ATTACH_EXTRACT_SCRIPT_TIMEOUT_SEC", "1800")
            ),

            attach_replicat_script_command=os.getenv("ATTACH_REPLICAT_SCRIPT_COMMAND", ""),
            attach_replicat_script_timeout_sec=int(
                os.getenv("ATTACH_REPLICAT_SCRIPT_TIMEOUT_SEC", "1800")
            ),
        )

    def validate(self) -> None:
        missing: list[str] = []

        if not self.oracle_user:
            missing.append("ORACLE_USER")
        if not self.oracle_password:
            missing.append("ORACLE_PASSWORD")
        if not self.oracle_dsn:
            missing.append("ORACLE_DSN")

        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        if self.build_desired_state_from_metadata and not self.metadata_dir:
            raise ValueError(
                "METADATA_DIR is required when BUILD_DESIRED_STATE_FROM_METADATA=true"
            )

        if self.prepare_source_action not in _ALLOWED_ACTIONS:
            raise ValueError("PREPARE_SOURCE_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")
        if self.attach_extract_action not in _ALLOWED_ACTIONS:
            raise ValueError("ATTACH_EXTRACT_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")
        if self.initial_load_action not in _ALLOWED_ACTIONS:
            raise ValueError("INITIAL_LOAD_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")
        if self.instantiation_action not in _ALLOWED_ACTIONS:
            raise ValueError("INSTANTIATION_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")
        if self.attach_replicat_action not in _ALLOWED_ACTIONS:
            raise ValueError("ATTACH_REPLICAT_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")
        if self.activation_action not in _ALLOWED_ACTIONS:
            raise ValueError("ACTIVATION_ACTION must be one of: SKIP, PLAN_ONLY, APPLY")

        if self.prepare_source_executor not in _ALLOWED_PREPARE_SOURCE_EXECUTORS:
            raise ValueError(
                "PREPARE_SOURCE_EXECUTOR must be one of: "
                "DRY_RUN, FILE_ONLY, OGG_REST_SKELETON, OGG_REST_REAL"
            )

        if self.attach_extract_executor not in _ALLOWED_ATTACH_EXTRACT_EXECUTORS:
            raise ValueError(
                "ATTACH_EXTRACT_EXECUTOR must be one of: "
                "DRY_RUN, FILE_ONLY, SCRIPT"
            )

        if self.initial_load_executor not in _ALLOWED_INITIAL_LOAD_EXECUTORS:
            raise ValueError(
                "INITIAL_LOAD_EXECUTOR must be one of: DRY_RUN, FILE_ONLY, SCRIPT"
            )

        if self.instantiation_executor not in _ALLOWED_INSTANTIATION_EXECUTORS:
            raise ValueError(
                "INSTANTIATION_EXECUTOR must be one of: DRY_RUN, FILE_ONLY, SCRIPT"
            )

        if self.attach_replicat_executor not in _ALLOWED_ATTACH_REPLICAT_EXECUTORS:
            raise ValueError(
                "ATTACH_REPLICAT_EXECUTOR must be one of: "
                "DRY_RUN, FILE_ONLY, SCRIPT"
            )


        if self.ogg_rest_mode not in {"OGG_REST_SKELETON", "OGG_REST_REAL"}:
            raise ValueError(
                "OGG_REST_MODE must be one of: OGG_REST_SKELETON, OGG_REST_REAL"
            )

        if self.trandata_scope not in {"TABLE", "SCHEMA"}:
            raise ValueError("TRANDATA_SCOPE must be one of: TABLE, SCHEMA")

        if (
            self.prepare_source_executor in {"OGG_REST_SKELETON", "OGG_REST_REAL"}
            and not self.ogg_rest_connection
        ):
            raise ValueError(
                "OGG_REST_CONNECTION is required for REST prepare_source"
            )

        if self.initial_load_executor == "SCRIPT" and not self.initial_load_script_command:
            raise ValueError(
                "INITIAL_LOAD_SCRIPT_COMMAND is required when INITIAL_LOAD_EXECUTOR=SCRIPT"
            )

        if self.attach_extract_executor == "SCRIPT" and not self.attach_extract_script_command:
            raise ValueError(
                "ATTACH_EXTRACT_SCRIPT_COMMAND is required when ATTACH_EXTRACT_EXECUTOR=SCRIPT"
            )

        if self.attach_replicat_executor == "SCRIPT" and not self.attach_replicat_script_command:
            raise ValueError(
                "ATTACH_REPLICAT_SCRIPT_COMMAND is required when ATTACH_REPLICAT_EXECUTOR=SCRIPT"
            )

        if self.instantiation_executor == "SCRIPT" and not self.instantiation_script_command:
            raise ValueError(
                "INSTANTIATION_SCRIPT_COMMAND is required when INSTANTIATION_EXECUTOR=SCRIPT"
            )