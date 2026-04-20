from __future__ import annotations


def resolve_instantiation_scn(
    registration_scn: int | None,
    instantiation_candidate_scn: int | None,
) -> int:
    if instantiation_candidate_scn is not None:
        return instantiation_candidate_scn
    if registration_scn is not None:
        return registration_scn
    raise ValueError("Cannot resolve instantiation SCN: both candidate and registration SCN are missing.")