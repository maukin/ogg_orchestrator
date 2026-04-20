from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractGroupConfig:
    group_name: str
    lines: list[str]


@dataclass(frozen=True)
class ReplicatGroupConfig:
    group_name: str
    lines: list[str]


@dataclass
class CDCConfigBundle:
    extract_groups: list[ExtractGroupConfig] = field(default_factory=list)
    replicat_groups: list[ReplicatGroupConfig] = field(default_factory=list)