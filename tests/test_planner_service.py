from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.services.planner_service import PlannerService


def test_planner_adds_plan_initial_load_for_existing_planned_table():
    desired = [
        DesiredTableConfig(
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
        )
    ]

    current = [
        TableRegistryRecord(
            table_id="SRCDB:PDB1:SRC.ORDERS->TGTDB:PDB2:DDS.ORDERS",
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
            actual_extract_group=None,
            actual_replicat_group=None,
            actual_load_batch_id=None,
            state=TableState.PLANNED,
            validation_status=ValidationStatus.UNKNOWN,
            prepared_for_instantiation=False,
            registration_scn=None,
            instantiation_scn=None,
            initial_load_started_at=None,
            initial_load_finished_at=None,
            cdc_capture_attached_at=None,
            cdc_apply_attached_at=None,
            activated_at=None,
            last_deployment_id=None,
            last_error_code=None,
            last_error_message=None,
            created_at=None,
            updated_at=None,
        )
    ]

    planner = PlannerService()
    plan = planner.build_plan(
        deployment_id="dep_1",
        environment_name="dev",
        git_branch="feature",
        git_commit_sha="abc",
        pipeline_id="1",
        desired_configs=desired,
        current_registry=current,
    )

    action_types = [a.action_type for a in plan.actions]
    assert "PLAN_INITIAL_LOAD" in action_types


def test_planner_adds_plan_cdc_only_for_existing_planned_table():
    desired = [
        DesiredTableConfig(
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.CDC_ONLY,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
        )
    ]

    current = [
        TableRegistryRecord(
            table_id="SRCDB:PDB1:SRC.ORDERS->TGTDB:PDB2:DDS.ORDERS",
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
            actual_extract_group=None,
            actual_replicat_group=None,
            actual_load_batch_id=None,
            state=TableState.PLANNED,
            validation_status=ValidationStatus.UNKNOWN,
            prepared_for_instantiation=False,
            registration_scn=None,
            instantiation_scn=None,
            initial_load_started_at=None,
            initial_load_finished_at=None,
            cdc_capture_attached_at=None,
            cdc_apply_attached_at=None,
            activated_at=None,
            last_deployment_id=None,
            last_error_code=None,
            last_error_message=None,
            created_at=None,
            updated_at=None,
        )
    ]

    planner = PlannerService()
    plan = planner.build_plan(
        deployment_id="dep_1",
        environment_name="dev",
        git_branch="feature",
        git_commit_sha="abc",
        pipeline_id="1",
        desired_configs=desired,
        current_registry=current,
    )

    action_types = [a.action_type for a in plan.actions]
    assert "PLAN_CDC_ONLY" in action_types


def test_planner_adds_plan_initial_load_only_for_existing_planned_table():
    desired = [
        DesiredTableConfig(
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_LOAD_ONLY,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
        )
    ]

    current = [
        TableRegistryRecord(
            table_id="SRCDB:PDB1:SRC.ORDERS->TGTDB:PDB2:DDS.ORDERS",
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
            actual_extract_group=None,
            actual_replicat_group=None,
            actual_load_batch_id=None,
            state=TableState.PLANNED,
            validation_status=ValidationStatus.UNKNOWN,
            prepared_for_instantiation=False,
            registration_scn=None,
            instantiation_scn=None,
            initial_load_started_at=None,
            initial_load_finished_at=None,
            cdc_capture_attached_at=None,
            cdc_apply_attached_at=None,
            activated_at=None,
            last_deployment_id=None,
            last_error_code=None,
            last_error_message=None,
            created_at=None,
            updated_at=None,
        )
    ]

    planner = PlannerService()
    plan = planner.build_plan(
        deployment_id="dep_1",
        environment_name="dev",
        git_branch="feature",
        git_commit_sha="abc",
        pipeline_id="1",
        desired_configs=desired,
        current_registry=current,
    )

    action_types = [a.action_type for a in plan.actions]
    assert "PLAN_INITIAL_LOAD_ONLY" in action_types
