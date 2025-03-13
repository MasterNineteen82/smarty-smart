"""
Smart Card Manager - Command Line Interface
Provides quick access to common card operations via terminal
"""

import sys
import argparse
import logging
from typing import List, Tuple, Optional

from card_utils import (
    establish_connection, close_connection, select_reader, 
    detect_card_type, is_card_registered, register_card, unregister_card, 
    backup_card_data, restore_card_data, secure_dispose_card,
    activate_card, deactivate_card, block_card, unblock_card,
    list_backups, delete_backup
)

# Constants
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(levelname)s: %(message)s'
DEFAULT_READER_PROMPT = "Enter reader number or name: "
CONFIRM_DISPOSE_MESSAGE = "WARNING: This will permanently erase all data from the card. Continue? (y/N): "
OPERATION_CANCELLED = "Operation cancelled"
NO_BACKUPS_FOUND = "No backups found"

# Logging Configuration
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger('cli')

def handle_card_operation(operation, *args, **kwargs):
    """
    Handles the execution of a card operation with centralized error handling.
    """
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error during {operation.__name__}: {str(e)}")
        return False, str(e)  # Consistent return of (success, message)

def select_card_reader(reader_identifier: Optional[str]) -> bool:
    """Selects a card reader based on the given identifier."""
    if reader_identifier is None:
        return True  # No reader specified, assume default or auto-select
    try:
        select_reader(reader_identifier)
        return True
    except Exception as e:
        logger.error(f"Error selecting reader: {str(e)}")
        print(f"Error selecting reader: {str(e)}")
        return False

def display_card_status():
    """Retrieves and displays the card status."""
    conn, err = establish_connection()
    if err:
        print(f"Error: {err}")
        return

    try:
        from smartcard.util import toHexString
        atr = toHexString(conn.getATR())
        card_type = detect_card_type(atr)
        registered = is_card_registered(atr)

        print(f"Card detected:")
        print(f"  ATR: {atr}")
        print(f"  Type: {card_type}")
        print(f"  Registered: {'Yes' if registered else 'No'}")
    except Exception as e:
        print(f"Error retrieving card status: {str(e)}")
    finally:
        close_connection(conn)

def list_readers() -> None:
    """List available card readers"""
    from smartcard.System import readers
    reader_list = readers()
    
    if not reader_list:
        print("No card readers found.")
        return
    
    print("Available readers:")
    for i, reader in enumerate(reader_list):
        print(f"  {i+1}. {reader}")

def execute_card_command(command: str, args: argparse.Namespace) -> None:
    """Execute a card command based on arguments"""
    if command == "list-readers":
        list_readers()
        return
    
    # Select reader if specified
    if args.reader is not None:
        try:
            select_reader(args.reader)
        except Exception as e:
            print(f"Error selecting reader: {str(e)}")
            return

    if command == "status":
        display_card_status()

    elif command == "register":
        if not args.name or not args.user_id:
            print("Error: name and user-id are required for registration")
            return

        try:
            success, message = register_card(args.name, args.user_id)
            print(message)
        except Exception as e:
            print(f"Error registering card: {str(e)}")

    elif command == "unregister":
        try:
            success, message = unregister_card()
            print(message)
        except Exception as e:
            print(f"Error unregistering card: {str(e)}")

    elif command == "activate":
        try:
            success, message = activate_card()
            print(message)
        except Exception as e:
            print(f"Error activating card: {str(e)}")

    elif command == "deactivate":
        try:
            success, message = deactivate_card()
            print(message)
        except Exception as e:
            print(f"Error deactivating card: {str(e)}")

    elif command == "block":
        try:
            success, message = block_card()
            print(message)
        except Exception as e:
            print(f"Error blocking card: {str(e)}")

    elif command == "unblock":
        try:
            success, message = unblock_card()
            print(message)
        except Exception as e:
            print(f"Error unblocking card: {str(e)}")

    elif command == "backup":
        try:
            success, message, backup_id = backup_card_data()
            print(message)
            if success:
                print(f"Backup ID: {backup_id}")
        except Exception as e:
            print(f"Error backing up card: {str(e)}")

    elif command == "restore":
        if not args.backup_id:
            print("Error: backup-id is required for restore operation")
            return

        try:
            success, message = restore_card_data(args.backup_id)
            print(message)
        except Exception as e:
            print(f"Error restoring card: {str(e)}")

    elif command == "list-backups":
        try:
            backups = list_backups()
            if not backups:
                print("No backups found")
                return

            print(f"Found {len(backups)} backups:")
            for backup in backups:
                print(f"  ID: {backup['backup_id']}")
                print(f"    Date: {backup['backup_time']}")
                print(f"    Card Type: {backup['card_type']}")
                print()
        except Exception as e:
            print(f"Error listing backups: {str(e)}")

    elif command == "delete-backup":
        if not args.backup_id:
            print("Error: backup-id is required for delete operation")
            return

        try:
            success, message = delete_backup(args.backup_id)
            print(message)
        except Exception as e:
            print(f"Error deleting backup: {str(e)}")

    elif command == "dispose":
        if not args.force:
            confirm = input("WARNING: This will permanently erase all data from the card. Continue? (y/N): ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return

        try:
            success, message = secure_dispose_card()
            print(message)
        except Exception as e:
            print(f"Error disposing card: {str(e)}")
        
        success, message = secure_dispose_card()
        print(message)

def create_parser() -> argparse.ArgumentParser:
    """Creates the argument parser for the CLI."""
    parser = argparse.ArgumentParser(description="Smart Card Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Define common argument
    reader_arg = {"help": "Specify reader number or name"}

    # Helper function to add common arguments
    def add_common_args(subparser):
        subparser.add_argument("--reader", **reader_arg)

    # List readers command
    list_readers_parser = subparsers.add_parser("list-readers", help="List available card readers")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show card status")
    add_common_args(status_parser)

    # Register command
    register_parser = subparsers.add_parser("register", help="Register a card")
    add_common_args(register_parser)
    register_parser.add_argument("--name", help="Card name", required=True)
    register_parser.add_argument("--user-id", help="User ID", required=True)

    # Unregister command
    unregister_parser = subparsers.add_parser("unregister", help="Unregister a card")
    add_common_args(unregister_parser)

    # Activate command
    activate_parser = subparsers.add_parser("activate", help="Activate a card")
    add_common_args(activate_parser)

    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a card")
    add_common_args(deactivate_parser)

    # Block command
    block_parser = subparsers.add_parser("block", help="Block a card")
    add_common_args(block_parser)

    # Unblock command
    unblock_parser = subparsers.add_parser("unblock", help="Unblock a card")
    add_common_args(unblock_parser)

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup a card")
    add_common_args(backup_parser)

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a card from backup")
    add_common_args(restore_parser)
    restore_parser.add_argument("--backup-id", help="Backup ID to restore", required=True)

    # List backups command
    list_backups_parser = subparsers.add_parser("list-backups", help="List available backups")

    # Delete backup command
    delete_backup_parser = subparsers.add_parser("delete-backup", help="Delete a backup")
    delete_backup_parser.add_argument("--backup-id", help="Backup ID to delete", required=True)

    # Dispose command
    dispose_parser = subparsers.add_parser("dispose", help="Securely dispose a card")
    add_common_args(dispose_parser)
    dispose_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    return parser

def main(args: List[str] = None) -> int:
    """Main entry point for the CLI application"""
    parser = create_parser()
    args = parser.parse_args(args)
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        execute_card_command(args.command, args)
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())