import re


_OGG_GROUP_NAME_RE = re.compile(r"^[A-Z_$][A-Z0-9_$]*$")


def validate_ogg_group_name(group_name: str) -> None:
    if not group_name:
        raise ValueError("OGG group name must not be empty")

    if len(group_name) > 8:
        raise ValueError(
            f"Invalid OGG group name '{group_name}': length must be <= 8"
        )

    if not _OGG_GROUP_NAME_RE.fullmatch(group_name):
        raise ValueError(
            f"Invalid OGG group name '{group_name}': must match ^[A-Z_$][A-Z0-9_$]*$"
        )