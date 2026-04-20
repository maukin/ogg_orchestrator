import argparse
import os

from app.repositories.table_metadata_repo import TableMetadataRepository
from app.services.desired_state_snapshot_builder import DesiredStateSnapshotBuilder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--git-commit-sha", default=os.getenv("CI_COMMIT_SHA"))
    parser.add_argument("--git-branch", default=os.getenv("CI_COMMIT_REF_NAME"))

    args = parser.parse_args()

    repo = TableMetadataRepository()
    builder = DesiredStateSnapshotBuilder()

    configs = repo.load_from_directory(args.metadata_dir)
    snapshot = builder.build_snapshot(
        environment=args.environment,
        configs=configs,
        git_commit_sha=args.git_commit_sha,
        git_branch=args.git_branch,
        source_dir=args.metadata_dir,
    )
    builder.write_snapshot(snapshot, args.output_json)

    print(
        f"Snapshot built successfully: {len(configs)} tables -> {args.output_json}"
    )


if __name__ == "__main__":
    main()