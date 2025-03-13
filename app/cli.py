"""
Command-line interface module for the Smartcard Manager application.

This module provides a comprehensive CLI for managing smart cards and NFC devices
with consistent error handling and user feedback.
"""

import logging
import sys
from typing import Optional

import click
from app.db import init_db
from app.core.card_manager import card_manager
from app.core.nfc import nfc_manager
from app.core.exceptions import (
    CardRegistrationError, CardNotFoundError, 
    CardOperationError, NFCOperationError,
    DatabaseError
)
from app.api.routes import bp as routes_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('smartcard-cli')

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Smartcard and NFC Manager CLI.
    
    Provides tools to manage smartcards and NFC devices in a unified interface.
    """
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    if verbose:
        logger.setLevel(logging.DEBUG)

@cli.command()
def initdb():
    """Initialize the database schema for card management."""
    try:
        init_db()
        click.echo("Database initialized successfully.")
        logger.info("Database initialized")
    except DatabaseError as e:
        logger.error(f"Database initialization failed: {e}")
        click.echo(f"Error initializing database: {e}", err=True)
        sys.exit(1)

@cli.command()
def list_cards():
    """List all registered cards in the system."""
    try:
        cards = card_manager.list_cards()
        if not cards:
            click.echo("No cards registered in the system.")
            return
            
        click.echo("Registered cards:")
        for card in cards:
            status = "ACTIVE" if card.is_active else "INACTIVE"
            blocked = " [BLOCKED]" if card.is_blocked else ""
            click.echo(f"ID: {card.id} | ATR: {card.atr} | User: {card.user_id} | Status: {status}{blocked}")
    except Exception as e:
        logger.error(f"Error listing cards: {e}")
        click.echo(f"Error retrieving card list: {e}", err=True)

@cli.command()
@click.argument('atr')
@click.argument('user_id')
@click.option('--activate', is_flag=True, help='Activate the card after registration')
def register_card(atr, user_id, activate):
    """Register a smart card with the given ATR to a user.
    
    ATR: The Answer To Reset string that uniquely identifies the card
    USER_ID: The ID of the user to associate with this card
    """
    try:
        card = card_manager.register_card(atr, user_id)
        click.echo(f"Card with ATR {atr} registered to user {user_id} (Card ID: {card.id}).")
        
        if activate:
            card_manager.activate_card(atr)
            click.echo(f"Card activated successfully.")
    except CardRegistrationError as e:
        logger.error(f"Card registration failed: {e}")
        click.echo(f"Error registering card: {e}", err=True)
    except CardOperationError as e:
        logger.error(f"Card activation failed: {e}")
        click.echo(f"Card registered but activation failed: {e}", err=True)

@cli.command()
@click.argument('card_identifier')
@click.option('--by-id', is_flag=True, help='Use card ID instead of ATR')
@click.confirmation_option(prompt='Are you sure you want to block this card?')
def block_card(card_identifier, by_id):
    """Block a smart card to prevent its usage.
    
    CARD_IDENTIFIER: The ATR string or ID of the card to block
    """
    try:
        if by_id:
            card = card_manager.block_card_by_id(int(card_identifier))
        else:
            card = card_manager.block_card(card_identifier)
        click.echo(f"Card {card_identifier} blocked successfully.")
    except CardNotFoundError as e:
        logger.error(f"Card not found: {e}")
        click.echo(f"Error: {e}", err=True)
    except CardOperationError as e:
        logger.error(f"Block operation failed: {e}")
        click.echo(f"Error blocking card: {e}", err=True)

@cli.command()
@click.argument('card_identifier')
@click.option('--by-id', is_flag=True, help='Use card ID instead of ATR')
def activate_card(card_identifier, by_id):
    """Activate a smart card for use.
    
    CARD_IDENTIFIER: The ATR string or ID of the card to activate
    """
    try:
        if by_id:
            card = card_manager.activate_card_by_id(int(card_identifier))
        else:
            card = card_manager.activate_card(card_identifier)
        click.echo(f"Card {card_identifier} activated successfully.")
    except CardNotFoundError as e:
        logger.error(f"Card not found: {e}")
        click.echo(f"Error: {e}", err=True)
    except CardOperationError as e:
        logger.error(f"Activation operation failed: {e}")
        click.echo(f"Error activating card: {e}", err=True)

@cli.command()
@click.argument('card_identifier')
@click.option('--by-id', is_flag=True, help='Use card ID instead of ATR')
def deactivate_card(card_identifier, by_id):
    """Deactivate a smart card.
    
    CARD_IDENTIFIER: The ATR string or ID of the card to deactivate
    """
    try:
        if by_id:
            card = card_manager.deactivate_card_by_id(int(card_identifier))
        else:
            card = card_manager.deactivate_card(card_identifier)
        click.echo(f"Card {card_identifier} deactivated successfully.")
    except CardNotFoundError as e:
        logger.error(f"Card not found: {e}")
        click.echo(f"Error: {e}", err=True)
    except CardOperationError as e:
        logger.error(f"Deactivation operation failed: {e}")
        click.echo(f"Error deactivating card: {e}", err=True)

@cli.command()
@click.argument('card_id', type=int)
@click.option('--raw', is_flag=True, help='Output raw data without formatting')
def read_nfc(card_id, raw):
    """Read data from an NFC card.
    
    CARD_ID: The ID of the NFC card to read from
    """
    try:
        data = nfc_manager.read_nfc_data(card_id)
        if raw:
            click.echo(data)
        else:
            click.echo(f"NFC data from card {card_id}: {data}")
    except CardNotFoundError as e:
        logger.error(f"NFC card not found: {e}")
        click.echo(f"Error: {e}", err=True)
    except NFCOperationError as e:
        logger.error(f"NFC read operation failed: {e}")
        click.echo(f"Error reading NFC data: {e}", err=True)

@cli.command()
@click.argument('card_id', type=int)
@click.argument('data')
@click.confirmation_option(prompt='Writing data will overwrite existing data. Continue?')
def write_nfc(card_id, data):
    """Write data to an NFC card.
    
    CARD_ID: The ID of the NFC card to write to
    DATA: The data string to write to the card
    """
    try:
        nfc_manager.write_nfc_data(card_id, data)
        click.echo(f"Data successfully written to NFC card {card_id}.")
    except CardNotFoundError as e:
        logger.error(f"NFC card not found: {e}")
        click.echo(f"Error: {e}", err=True)
    except NFCOperationError as e:
        logger.error(f"NFC write operation failed: {e}")
        click.echo(f"Error writing NFC data: {e}", err=True)

@cli.command()
def scan_devices():
    """Scan for connected NFC readers and smart card devices."""
    try:
        devices = nfc_manager.scan_devices()
        if not devices:
            click.echo("No NFC or smartcard devices detected.")
            return
            
        click.echo("Detected devices:")
        for i, device in enumerate(devices, 1):
            click.echo(f"{i}. {device.name} ({device.device_type})")
    except NFCOperationError as e:
        logger.error(f"Device scanning failed: {e}")
        click.echo(f"Error scanning for devices: {e}", err=True)

if __name__ == '__main__':
    cli()