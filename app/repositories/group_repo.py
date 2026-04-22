from __future__ import annotations

import oracledb

from app.models.groups import GroupConfig


class GroupRepository:
    def __init__(self, connection: oracledb.Connection):
        self.connection = connection

    def list_active_groups(self, environment_name: str) -> list[GroupConfig]:
        sql = """
            SELECT
                group_name,
                group_type,
                environment_name,
                source_system,
                target_system,
                max_tables,
                priority_class,
                active_flag,
                notes
            FROM etl_group_registry
            WHERE environment_name = :environment_name
              AND active_flag = 'Y'
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {"environment_name": environment_name})
            rows = cursor.fetchall()

        return [
            GroupConfig(
                group_name=row[0],
                group_type=row[1],
                environment_name=row[2],
                source_system=row[3],
                target_system=row[4],
                max_tables=row[5],
                priority_class=row[6],
                active_flag=(row[7] == "Y"),
                notes=row[8],
            )
            for row in rows
        ]

    def create_group(self, group: GroupConfig) -> None:
        existing = self.get_group(
            group_name=group.group_name,
            environment_name=group.environment_name,
        )
        if existing is not None:
            return

        sql = """
            INSERT INTO etl_group_registry (
                group_name,
                group_type,
                environment_name,
                source_system,
                target_system,
                max_tables,
                priority_class,
                active_flag,
                notes
            ) VALUES (
                :group_name,
                :group_type,
                :environment_name,
                :source_system,
                :target_system,
                :max_tables,
                :priority_class,
                :active_flag,
                :notes
            )
        """
        params = {
            "group_name": group.group_name,
            "group_type": group.group_type,
            "environment_name": group.environment_name,
            "source_system": group.source_system,
            "target_system": group.target_system,
            "max_tables": group.max_tables,
            "priority_class": group.priority_class,
            "active_flag": "Y" if group.active_flag else "N",
            "notes": group.notes,
        }

        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)

        self.connection.commit()

    def get_group(
        self,
        *,
        group_name: str,
        environment_name: str,
    ) -> GroupConfig | None:
        sql = """
            SELECT
                group_name,
                group_type,
                environment_name,
                source_system,
                target_system,
                max_tables,
                priority_class,
                active_flag,
                notes
            FROM etl_group_registry
            WHERE group_name = :group_name
              AND environment_name = :environment_name
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "group_name": group_name,
                    "environment_name": environment_name,
                },
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return GroupConfig(
            group_name=row[0],
            group_type=row[1],
            environment_name=row[2],
            source_system=row[3],
            target_system=row[4],
            max_tables=row[5],
            priority_class=row[6],
            active_flag=(row[7] == "Y"),
            notes=row[8],
        )