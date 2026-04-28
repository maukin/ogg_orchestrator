from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractBaseConfigParams:
    group_name: str
    credential_alias: str
    trail_name: str
    integrated: bool = True
    max_sga_size_mb: int = 128


@dataclass(frozen=True)
class ReplicatBaseConfigParams:
    group_name: str
    credential_alias: str
    batchsql: bool = True
    getupdatebefores: bool = True
    insertallrecords: bool = True


class OGGBaseConfigFactory:
    def build_extract_base_config(self, params: ExtractBaseConfigParams) -> list[str]:
        lines = [
            f"EXTRACT {params.group_name}",
            f"USERIDALIAS {params.credential_alias}",
            f"EXTTRAIL {params.trail_name}",
        ]
        if params.integrated:
            lines.append(
                f"TRANLOGOPTIONS INTEGRATEDPARAMS (max_sga_size {params.max_sga_size_mb})"
            )
        return lines

    def build_replicat_base_config(self, params: ReplicatBaseConfigParams) -> list[str]:
        lines = [
            f"REPLICAT {params.group_name}",
            f"USERIDALIAS {params.credential_alias}",
        ]
        if params.insertallrecords:
            lines.append("INSERTALLRECORDS")
        if params.getupdatebefores:
            lines.append("GETUPDATEBEFORES")
        if params.batchsql:
            lines.append("BATCHSQL")
        return lines