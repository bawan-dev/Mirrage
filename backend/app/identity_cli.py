"""Local administrative CLI for first-owner bootstrap and identity backups."""

from __future__ import annotations

import argparse

from backend.app.services.backups import (
    create_identity_backup,
    restore_identity_backup,
)
from backend.app.services.identity_store import IdentityConflictError, identity_store


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local Mirrage identity data.")
    commands = parser.add_subparsers(dest="command", required=True)

    bootstrap = commands.add_parser(
        "bootstrap-owner", help="Create the first owner and optional trusted device."
    )
    bootstrap.add_argument("--name", required=True, help="Owner display name.")
    bootstrap.add_argument(
        "--device-name", help="Name for the first trusted mirror/admin device."
    )
    bootstrap.add_argument(
        "--device-type",
        default="mirror",
        choices=(
            "mirror",
            "phone",
            "desktop",
            "tablet",
            "vehicle",
            "wearable",
            "room_node",
            "other",
        ),
    )

    backup = commands.add_parser("backup", help="Create an identity database backup.")
    backup.add_argument("--destination", help="Optional backup directory.")

    restore = commands.add_parser(
        "restore", help="Restore a validated identity database backup."
    )
    restore.add_argument("--path", required=True, help="Backup file to restore.")
    return parser


def bootstrap_owner(name: str, device_name: str | None, device_type: str) -> int:
    identity_store.initialize()
    if identity_store.user_count() != 0:
        raise IdentityConflictError(
            "Owner bootstrap is only available before the first user exists."
        )

    owner = identity_store.create_user(
        display_name=name,
        role="owner",
        household_member=True,
    )
    identity_store.append_audit_event(
        event_type="owner_bootstrapped",
        action="identity.bootstrap_owner",
        resource_type="identity_user",
        resource_id=owner.public_id,
        result="success",
    )
    print(f"Owner created: {owner.display_name} ({owner.public_id})")

    if device_name:
        enrollment = identity_store.enroll_device(
            user_public_id=owner.public_id,
            display_name=device_name,
            device_type=device_type,
            trust_level="privileged",
        )
        identity_store.append_audit_event(
            event_type="device_enrolled",
            action="identity.bootstrap_device",
            resource_type="trusted_device",
            resource_id=enrollment.device.public_id,
            result="success",
            metadata={"device_type": device_type, "trust_level": "privileged"},
        )
        print(f"Trusted device created: {enrollment.device.public_id}")
        print("Device token (shown once):")
        print(enrollment.token)
    return 0


def main() -> int:
    arguments = _parser().parse_args()
    if arguments.command == "bootstrap-owner":
        return bootstrap_owner(
            arguments.name, arguments.device_name, arguments.device_type
        )
    if arguments.command == "backup":
        result = create_identity_backup(arguments.destination)
        print(f"Identity backup created: {result.destination}")
        return 0
    if arguments.command == "restore":
        result = restore_identity_backup(arguments.path)
        print(f"Identity backup restored: {result.destination}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
