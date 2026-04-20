from dataclasses import dataclass
import os


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
    prepare_source_mode: str
    prepare_source_executor: str
    attach_extract_mode: str
    attach_extract_executor: str
    initial_load_mode: str
    initial_load_executor: str
    instantiation_mode: str
    instantiation_executor: str
    attach_replicat_mode: str
    attach_replicat_executor: str
    activation_mode: str
    activation_executor: str
    ogg_rest_base_url: str
    ogg_rest_username: str
    ogg_rest_password: str
    ogg_rest_deployment_name: str
    ogg_rest_verify_ssl: bool
    ogg_rest_mode: str
    allow_real_prepare_source: bool
    ogg_rest_connection: str
    trandata_scope: str
    initial_load_script_path: str
    initial_load_script_timeout_sec: int
    initial_load_script_command: str
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
            build_desired_state_from_metadata=(
                os.getenv("BUILD_DESIRED_STATE_FROM_METADATA", "false").lower() == "true"
            ),
            metadata_dir=os.getenv("METADATA_DIR", "metadata"),
            desired_state_path=os.getenv("DESIRED_STATE_PATH", "registry/desired_state.json"),
            git_branch=os.getenv("CI_COMMIT_REF_NAME"),
            git_commit_sha=os.getenv("CI_COMMIT_SHA"),
            pipeline_id=os.getenv("CI_PIPELINE_ID"),
            prepare_source_mode=os.getenv("PREPARE_SOURCE_MODE", "DRY_RUN").upper(),
            prepare_source_executor=os.getenv("PREPARE_SOURCE_EXECUTOR", "DRY_RUN").upper(),
            attach_extract_mode=os.getenv("ATTACH_EXTRACT_MODE", "DRY_RUN").upper(),
            attach_extract_executor=os.getenv("ATTACH_EXTRACT_EXECUTOR", "DRY_RUN").upper(),
            initial_load_mode=os.getenv("INITIAL_LOAD_MODE", "DRY_RUN").upper(),
            initial_load_executor=os.getenv("INITIAL_LOAD_EXECUTOR", "DRY_RUN").upper(),
            instantiation_mode=os.getenv("INSTANTIATION_MODE", "DRY_RUN").upper(),
            instantiation_executor=os.getenv("INSTANTIATION_EXECUTOR", "DRY_RUN").upper(),
            attach_replicat_mode=os.getenv("ATTACH_REPLICAT_MODE", "DRY_RUN").upper(),
            attach_replicat_executor=os.getenv("ATTACH_REPLICAT_EXECUTOR", "DRY_RUN").upper(),
            activation_mode=os.getenv("ACTIVATION_MODE", "DRY_RUN").upper(),
            activation_executor=os.getenv("ACTIVATION_EXECUTOR", "DRY_RUN").upper(),
            ogg_rest_base_url=os.getenv("OGG_REST_BASE_URL", ""),
            ogg_rest_username=os.getenv("OGG_REST_USERNAME", ""),
            ogg_rest_password=os.getenv("OGG_REST_PASSWORD", ""),
            ogg_rest_deployment_name=os.getenv("OGG_REST_DEPLOYMENT_NAME", ""),
            ogg_rest_verify_ssl=os.getenv("OGG_REST_VERIFY_SSL", "true").lower() == "true",
            ogg_rest_mode=os.getenv("OGG_REST_MODE", "OGG_REST_SKELETON").upper(),
            allow_real_prepare_source=os.getenv("ALLOW_REAL_PREPARE_SOURCE", "false").lower() == "true",
            ogg_rest_connection=os.getenv("OGG_REST_CONNECTION", ""),
            trandata_scope=os.getenv("TRANDATA_SCOPE", "TABLE").upper(),
            initial_load_script_path=os.getenv("INITIAL_LOAD_SCRIPT_PATH", ""),
            initial_load_script_timeout_sec=int(os.getenv("INITIAL_LOAD_SCRIPT_TIMEOUT_SEC", "3600")),
            initial_load_script_command=os.getenv("INITIAL_LOAD_SCRIPT_COMMAND", ""),
            attach_extract_script_command=os.getenv("ATTACH_EXTRACT_SCRIPT_COMMAND", ""),
            attach_extract_script_timeout_sec=int(os.getenv("ATTACH_EXTRACT_SCRIPT_TIMEOUT_SEC", "1800")),
            attach_replicat_script_command=os.getenv("ATTACH_REPLICAT_SCRIPT_COMMAND", ""),
            attach_replicat_script_timeout_sec=int(os.getenv("ATTACH_REPLICAT_SCRIPT_TIMEOUT_SEC", "1800")),
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

        if self.prepare_source_mode not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("PREPARE_SOURCE_MODE must be one of: DRY_RUN, FILE_ONLY")

        if self.prepare_source_executor not in {"DRY_RUN", "FILE_ONLY", "OGG_REST_SKELETON", "OGG_REST_REAL"}:
            raise ValueError(
                "PREPARE_SOURCE_EXECUTOR must be one of: DRY_RUN, FILE_ONLY, OGG_REST_SKELETON, OGG_REST_REAL"
            )

        if self.attach_extract_mode not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("ATTACH_EXTRACT_MODE must be one of: DRY_RUN, FILE_ONLY")

        if self.attach_extract_executor not in {"DRY_RUN", "OGG_REST_SKELETON", "OGG_REST_REAL", "FILE_ONLY", "SCRIPT"}:
            raise ValueError(
                "ATTACH_EXTRACT_EXECUTOR must be one of: DRY_RUN, OGG_REST_SKELETON, OGG_REST_REAL, FILE_ONLY, SCRIPT"
            )

        if self.initial_load_mode not in {"DRY_RUN", "FILE_ONLY", "SCRIPT"}:
            raise ValueError("INITIAL_LOAD_MODE must be one of: DRY_RUN, FILE_ONLY, SCRIPT")

        if self.initial_load_executor not in {"DRY_RUN", "FILE_ONLY", "SCRIPT"}:
            raise ValueError("INITIAL_LOAD_EXECUTOR must be one of: DRY_RUN, FILE_ONLY, SCRIPT")

        if self.initial_load_executor == "SCRIPT" and not self.initial_load_script_command:
            raise ValueError("INITIAL_LOAD_SCRIPT_COMMAND is required when INITIAL_LOAD_EXECUTOR=SCRIPT")

        if self.instantiation_mode not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("INSTANTIATION_MODE must be one of: DRY_RUN, FILE_ONLY")

        if self.instantiation_executor not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("INSTANTIATION_EXECUTOR must be one of: DRY_RUN, FILE_ONLY")

        if self.attach_replicat_mode not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("ATTACH_REPLICAT_MODE must be one of: DRY_RUN, FILE_ONLY")

        if self.attach_replicat_executor not in {"DRY_RUN", "OGG_REST_SKELETON", "OGG_REST_REAL", "FILE_ONLY", "SCRIPT"}:
            raise ValueError(
                "ATTACH_REPLICAT_EXECUTOR must be one of: DRY_RUN, OGG_REST_SKELETON, OGG_REST_REAL, FILE_ONLY, SCRIPT"
            )

        if self.activation_mode not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("ACTIVATION_MODE must be one of: DRY_RUN, FILE_ONLY")

        if self.activation_executor not in {"DRY_RUN", "FILE_ONLY"}:
            raise ValueError("ACTIVATION_EXECUTOR must be one of: DRY_RUN, FILE_ONLY")

        if self.ogg_rest_mode not in {"OGG_REST_SKELETON", "OGG_REST_REAL"}:
            raise ValueError("OGG_REST_MODE must be one of: OGG_REST_SKELETON, OGG_REST_REAL")

        if self.ogg_rest_mode == "OGG_REST_REAL" and not self.allow_real_prepare_source:
            # глобально не запрещаем, но prepare_source будет отдельно проверяться в main.py
            pass

        if self.trandata_scope not in {"TABLE", "SCHEMA"}:
            raise ValueError("TRANDATA_SCOPE must be one of: TABLE, SCHEMA")

        if self.prepare_source_executor in {"OGG_REST_SKELETON", "OGG_REST_REAL"} and not self.ogg_rest_connection:
            raise ValueError("OGG_REST_CONNECTION is required for REST prepare_source")

        if self.attach_extract_executor == "SCRIPT" and not self.attach_extract_script_command:
            raise ValueError("ATTACH_EXTRACT_SCRIPT_COMMAND is required when ATTACH_EXTRACT_EXECUTOR=SCRIPT")

        if self.attach_replicat_executor == "SCRIPT" and not self.attach_replicat_script_command:
            raise ValueError("ATTACH_REPLICAT_SCRIPT_COMMAND is required when ATTACH_REPLICAT_EXECUTOR=SCRIPT")
