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