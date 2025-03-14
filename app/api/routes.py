import datetime
import time
import json
import os
from functools import wraps
from typing import Optional

from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from smartcard.System import readers
from smartcard.scard import *  # noqa - Import all names from smartcard.scard

from app.core.card_utils import (
    safe_globals, card_status, CardStatus, pin_attempts, MAX_PIN_ATTEMPTS, logger,
    detect_card_type, is_card_registered, detect_reader_type
)

from app.device_manager import detect_readers, get_device_info, configure_device, update_firmware, monitor_device_health
from app.core.card_manager import card_manager, CardError
from app.core.card_lifecycle import card_lifecycle_manager
from app.security_manager import security_manager
from app import get_models, get_api, get_core

# Import pyscard modules
from smartcard.Exceptions import CardConnectionException
from smartcard.CardConnection import CardConnection
from smartcard.CardService import CardService
from smartcard.util import toHexString, toBytes

# Import response utilities
from app.utils.response_utils import standard_response, error_response

models = get_models()
core = get_core()

# Define selected_reader (replace with actual logic to select a reader)
selected_reader = None

# Define update_available_readers (replace with actual implementation)
def update_available_readers():
    """Updates the list of available smart card readers."""
    try:
        return detect_readers()
    except Exception as e:
        logger.error(f"Error detecting readers: {e}")
        return []

# Define status (replace with actual implementation)
status = "OK"

def load_config():
    config = {}
    config['MAX_PIN_ATTEMPTS'] = int(os.environ.get('MAX_PIN_ATTEMPTS', 3))
    config['DEFAULT_PIN'] = os.environ.get('DEFAULT_PIN', '123')
    return config

config = load_config()
MAX_PIN_ATTEMPTS = config['MAX_PIN_ATTEMPTS']
DEFAULT_PIN = config['DEFAULT_PIN']

def handle_card_exceptions(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Value error: {e}")
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(e),
                    error_type="ValueError"
                )
            )
        except KeyError as e:
            logger.warning(f"Key error: {e}")
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(e),
                    error_type="KeyError"
                )
            )
        except CardConnectionException as e:
            logger.error(f"Card connection error: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="CardConnectionError",
                    suggestion="Check card and reader"
                )
            )
        except Exception as e:
            logger.exception(f"Operation failed: {e}")
            suggestion = None
            if "No card present" in str(e):
                suggestion = "Please place a card on the reader"
            elif "Connection failed" in str(e):
                suggestion = "Check if reader is properly connected"
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type=e.__class__.__name__,
                    suggestion=suggestion
                )
            )
    return decorated_function

# REMOVED duplicate error_response function (lines 92-100)

def log_operation_timing(operation_name):
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting operation: {operation_name}")
            
            try:
                result = await f(*args, **kwargs)
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                logger.debug(f"Operation completed: {operation_name} in {duration:.2f}ms")
                return result
            except Exception as e:
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                logger.error(f"Operation failed: {operation_name} after {duration:.2f}ms - {e}")
                raise
            finally:
                logger.debug(f"Operation {operation_name} finished, total duration: {duration:.2f}ms")
                
        return wrapper
    return decorator

router = APIRouter()

def establish_connection(reader_name=None):
    try:
        global selected_reader
        if not reader_name:
            if not selected_reader:
                return None, "No reader selected"
            reader_name = selected_reader.name
        
        reader = readers()[0]  # Get the first reader
        connection = reader.createConnection()
        connection.connect()
        return connection, None
    except Exception as e:
        logger.error(f"Failed to establish connection: {e}")
        return None, str(e)

def close_connection(conn):
    try:
        if conn:
            conn.disconnect()
    except Exception as e:
        logger.error(f"Failed to close connection: {e}")

@router.get("/")
async def index():
    try:
        reader_list = update_available_readers()
        readers_str = [str(r) for r in reader_list]
        return standard_response(
            message="API index retrieved successfully",
            data={"status": status, "readers": readers_str}
        )
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Error rendering index page",
                error_type="ServerError",
                suggestion="Please try again later"
            )
        )

@router.post('/start_server', endpoint='start_server')
@log_operation_timing("Start Server")
@handle_card_exceptions
async def start_server_route():
    try:
        # from app.app import app # no flask app
        # run_server(app) # no flask app
        return standard_response(
            message="Server start not implemented",
            data={"status": "success"}
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message=f"Failed to start server: {str(e)}",
                error_type="ServerStartError"
            )
        )

@router.post('/card_status', endpoint='card_status')
@log_operation_timing("Card Status")
@handle_card_exceptions
async def get_card_status():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            logger.warning(f"Connection error: {err}")
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check if reader is connected"
                )
            )
        
        try:
            status_data = get_card_status_data(conn)
            return standard_response(
                message="Card status retrieved successfully",
                data=status_data
            )
        finally:
            close_connection(conn)

@router.post('/stop_server', endpoint='stop_server')
@log_operation_timing("Stop Server")
@handle_card_exceptions
async def stop_server_route():
    try:
        # stop_server() # no flask app
        return standard_response(
            message="Server stop not implemented",
            data={"status": "success"}
        )
    except Exception as e:
        logger.error(f"Failed to stop server: {e}")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message=f"Failed to stop server: {str(e)}",
                error_type="ServerStopError"
            )
        )

@router.post('/connect', endpoint='connect_card')
@log_operation_timing("Connect Card")
@handle_card_exceptions
async def connect_card():
    reader_list = [str(r) for r in readers()]
    if not reader_list:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message="No readers detected",
                error_type="ReaderNotFoundError",
                suggestion="Please check card reader connection"
            )
        )

    results = []
    for r in reader_list:
        conn, err = establish_connection(r)
        results.append({"reader": r, "success": conn is not None, "message": err or "Connected successfully"})
        if conn:
            close_connection(conn)

    return standard_response(
        message="Card reader connection test results",
        data={"results": results}
    )

@router.post('/read_memory', endpoint='read_memory')
@log_operation_timing("Read Memory")
async def read_memory():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        try:
            apdu = [0xFF, 0xB0, 0x00, 0x00, 0x100]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
                return standard_response(
                    message="Memory read successfully",
                    data={
                        "hex_data": hex_data,
                        "ascii_data": ascii_data
                    }
                )
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}",
                    error_type="MemoryReadError"
                )
            )
        finally:
            close_connection(conn)

class VerifyPinRequest(BaseModel):
    pin: Optional[str] = None

@router.post('/verify_pin', endpoint='verify_pin')
@log_operation_timing("Verify PIN")
async def verify_pin(request: VerifyPinRequest):
    global pin_attempts, card_status
    with safe_globals():
        if pin_attempts >= MAX_PIN_ATTEMPTS:
            card_status = CardStatus.BLOCKED
            return JSONResponse(
                status_code=403,
                content=error_response(
                    message="Card blocked: Too many PIN attempts",
                    error_type="CardBlockedError",
                    suggestion="Reset card or contact administrator"
                )
            )

        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )

        try:
            pin = request.pin or DEFAULT_PIN
            if not isinstance(pin, str) or len(pin) != 3 or not pin.isdigit():
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="PIN must be a 3-digit number",
                        error_type="ValidationError",
                        suggestion="Please provide a 3-digit PIN"
                    )
                )

            # Use security_manager to verify PIN
            if security_manager.verify_pin(pin):
                pin_attempts = 0
                return standard_response(
                    message="PIN verified successfully"
                )
            else:
                pin_attempts += 1
                remaining = MAX_PIN_ATTEMPTS - pin_attempts
                msg = f"PIN verification failed: {remaining} attempts left"
                if pin_attempts >= MAX_PIN_ATTEMPTS:
                    card_status = CardStatus.BLOCKED
                    msg += " Card blocked."
                
                return JSONResponse(
                    status_code=401,
                    content=error_response(
                        message=msg,
                        error_type="InvalidPinError",
                        suggestion="Please check your PIN and try again"
                    )
                )
        finally:
            close_connection(conn)

class UpdatePinRequest(BaseModel):
    pin: str

@router.post('/update_pin', endpoint='update_pin')
async def update_pin(request: UpdatePinRequest):
    global pin_attempts, card_status
    with safe_globals():
        if pin_attempts >= MAX_PIN_ATTEMPTS:
            return JSONResponse(
                status_code=403,
                content=error_response(
                    message="Card blocked: Too many PIN attempts",
                    error_type="CardBlockedError",
                    suggestion="Reset card or contact administrator"
                )
            )
        
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        
        try:
            new_pin = request.pin
            if not isinstance(new_pin, str) or len(new_pin) != 3 or not new_pin.isdigit():
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="New PIN must be a 3-digit number",
                        error_type="ValidationError",
                        suggestion="Please provide a 3-digit PIN"
                    )
                )
            
            verify_apdu = [0xFF, 0x20, 0x00, 0x00, 0x03, 0x31, 0x32, 0x33]
            _, sw1, sw2 = conn.transmit(verify_apdu)
            if sw1 != 0x90 or sw2 != 0x00:
                pin_attempts += 1
                return JSONResponse(
                    status_code=401,
                    content=error_response(
                        message=f"Current PIN verification failed: SW1={sw1:02X}, SW2={sw2:02X}",
                        error_type="InvalidPinError",
                        suggestion="Please check your current PIN"
                    )
                )
            
            pin_bytes = [ord(c) for c in new_pin]
            apdu = [0xFF, 0xD0, 0x00, 0x00, 0x03] + pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                pin_attempts = 0
                return standard_response(
                    message="PIN updated successfully"
                )
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=f"PIN update failed: SW1={sw1:02X}, SW2={sw2:02X}",
                    error_type="PinUpdateError"
                )
            )
        finally:
            close_connection(conn)

@router.get('/card_info', endpoint='card_info')
@log_operation_timing("Get Card Info")
@handle_card_exceptions
async def get_card_info():
    """Get information about the currently inserted card"""
    with safe_globals():
        conn, err = establish_connection()
        if err:
            logger.warning(f"Connection error: {err}")
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check if reader is connected"
                )
            )
        
        try:
            card_data = get_card_data(conn)
            return standard_response(
                message="Card information retrieved successfully",
                data=card_data
            )
        finally:
            close_connection(conn)

class ReadMemoryRegionRequest(BaseModel):
    offset: int = 0
    length: int = 16

@router.post('/read_memory_region', endpoint='read_memory_region')
@log_operation_timing("Read Memory Region")
async def read_memory_region(request: ReadMemoryRegionRequest):
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        
        try:
            offset = request.offset
            length = request.length
            if offset < 0 or length < 1 or offset + length > 256:
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="Invalid offset or length",
                        error_type="ValidationError",
                        suggestion="Offset must be >= 0 and offset+length <= 256"
                    )
                )
            
            apdu = [0xFF, 0xB0, offset >> 8, offset & 0xFF, length]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                return standard_response(
                    message="Memory region read successfully",
                    data={"hex_data": hex_data}
                )
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}",
                    error_type="MemoryReadError"
                )
            )
        finally:
            close_connection(conn)

class WriteMemoryRequest(BaseModel):
    offset: int = 0
    data: str

@router.post('/write_memory', endpoint='write_memory')
@log_operation_timing("Write Memory")
async def write_memory(request: WriteMemoryRequest):
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        
        try:
            offset = request.offset
            data_hex = request.data.replace(' ', '')
            if offset < 0 or not all(c in '0123456789ABCDEFabcdef' for c in data_hex):
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="Invalid offset or data",
                        error_type="ValidationError",
                        suggestion="Offset must be >= 0 and data must be valid hex"
                    )
                )
            
            data_bytes = toBytes(data_hex)
            if offset + len(data_bytes) > 256:
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="Data exceeds card capacity",
                        error_type="ValidationError",
                        suggestion="Reduce data size or change offset"
                    )
                )
            
            apdu = [0xFF, 0xD6, offset >> 8, offset & 0xFF, len(data_bytes)] + list(data_bytes)
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                return standard_response(
                    message="Write operation completed successfully"
                )
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=f"Write failed: SW1={sw1:02X}, SW2={sw2:02X}",
                    error_type="MemoryWriteError"
                )
            )
        finally:
            close_connection(conn)

@router.post('/change_pin', endpoint='change_pin')
@log_operation_timing("Change PIN")
async def change_pin():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        
        try:
            return JSONResponse(
                status_code=501,
                content=error_response(
                    message="PIN change functionality not implemented",
                    error_type="NotImplementedError",
                    suggestion="Use update_pin endpoint instead"
                )
            )
        finally:
            close_connection(conn)

@router.get('/card_status', endpoint='get_card_status')
@log_operation_timing("Get Card Status")
@handle_card_exceptions
async def card_status_get():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )
        
        try:
            return JSONResponse(
                status_code=501,
                content=error_response(
                    message="GET card status functionality not implemented",
                    error_type="NotImplementedError",
                    suggestion="Use POST /card_status endpoint instead"
                )
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )
        finally:
            close_connection(conn)

@router.post('/format_card', endpoint='format_card')
@log_operation_timing("Format Card")
@handle_card_exceptions
async def format_card():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )

        try:
            format_apdu = [0xFF, 0x00, 0x00, 0x00, 0x00]
            data, sw1, sw2 = conn.transmit(format_apdu)

            if sw1 == 0x90 and sw2 == 0x00:
                return standard_response(
                    message="Card formatted successfully"
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=error_response(
                        message=f"Format failed: SW1={sw1:02X}, SW2={sw2:02X}",
                        error_type="CardFormatError"
                    )
                )

        except Exception as e:
            logger.error(f"Error formatting card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )
        finally:
            close_connection(conn)

class BlockCardRequest(BaseModel):
    atr: str

@router.post('/block_card_direct', endpoint='block_card_direct')
@log_operation_timing("Block Card (Direct)")
@handle_card_exceptions
async def block_card_direct(request: BlockCardRequest):
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )

        try:
            atr = request.atr
            if not atr:
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="ATR is required",
                        error_type="ValidationError"
                    )
                )

            # Use CardLifecycleManager to block the card
            success, message, _ = card_lifecycle_manager.block_existing_card(atr)
            if success:
                return standard_response(
                    message=message
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=error_response(
                        message=message,
                        error_type="CardBlockError"
                    )
                )

        except Exception as e:
            logger.error(f"Error blocking card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )
        finally:
            close_connection(conn)

class RegisterCardRequest(BaseModel):
    user_id: str

@router.post('/register_card', endpoint='register_card')
@log_operation_timing("Register Card")
@handle_card_exceptions
async def register_card_route(request: RegisterCardRequest):
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=str(err),
                    error_type="ConnectionError",
                    suggestion="Check reader connection"
                )
            )

        try:
            atr = toHexString(conn.getATR())
            user_id = request.user_id

            if not user_id:
                return JSONResponse(
                    status_code=400,
                    content=error_response(
                        message="User ID is required",
                        error_type="ValidationError"
                    )
                )

            # Use CardLifecycleManager to register the card
            success, message = card_lifecycle_manager.register_new_card(atr, user_id)
            if success:
                return standard_response(
                    message=message
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=error_response(
                        message=message,
                        error_type="CardRegistrationError"
                    )
                )

        except CardError as e:
            logger.error(f"Error registering card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="CardError"
                )
            )
        except Exception as e:
            logger.error(f"Error registering card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )
        finally:
            close_connection(conn)

class UnregisterCardRequest(BaseModel):
    atr: str

@router.post('/unregister_card', endpoint='unregister_card')
@log_operation_timing("Unregister Card")
@handle_card_exceptions
async def unregister_card(request: UnregisterCardRequest):
    with safe_globals():
        atr = request.atr
        if not atr:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message="ATR is required",
                    error_type="ValidationError"
                )
            )
        try:
            # Use CardLifecycleManager to unregister the card
            # Implementation is commented out in original code
            return JSONResponse(
                status_code=501,
                content=error_response(
                    message="Card unregistration functionality not implemented",
                    error_type="NotImplementedError"
                )
            )
        except Exception as e:
            logger.error(f"Error unregistering card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )

@router.get('/check_registration', endpoint='check_registration')
@log_operation_timing("Check Card Registration")
@handle_card_exceptions
async def check_registration(atr: str):
    if not atr:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message="ATR is required",
                error_type="ValidationError"
            )
        )
    try:
        is_registered = card_manager.is_card_registered(atr)
        return standard_response(
            message="Card registration status retrieved successfully",
            data={"is_registered": is_registered}
        )
    except Exception as e:
        logger.error(f"Error checking card registration: {e}")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message=str(e),
                error_type="ServerError"
            )
        )

class CardActionRequest(BaseModel):
    atr: str

@router.post('/activate_card', endpoint='activate_card')
@log_operation_timing("Activate Card")
@handle_card_exceptions
async def activate_card(request: CardActionRequest):
    with safe_globals():
        atr = request.atr
        if not atr:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message="ATR is required",
                    error_type="ValidationError"
                )
            )
        try:
            # Use CardLifecycleManager to activate the card
            success, message, _ = card_lifecycle_manager.activate_existing_card(atr)
            if success:
                return standard_response(
                    message=message
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=error_response(
                        message=message,
                        error_type="CardActivationError"
                    )
                )
        except Exception as e:
            logger.error(f"Error activating card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )

@router.post('/deactivate_card', endpoint='deactivate_card')
@log_operation_timing("Deactivate Card")
@handle_card_exceptions
async def deactivate_card(request: CardActionRequest):
    with safe_globals():
        atr = request.atr
        if not atr:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message="ATR is required",
                    error_type="ValidationError"
                )
            )
        try:
            # Use CardLifecycleManager to deactivate the card
            success, message, _ = card_lifecycle_manager.deactivate_existing_card(atr)
            if success:
                return standard_response(
                    message=message
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=error_response(
                        message=message,
                        error_type="CardDeactivationError"
                    )
                )
        except Exception as e:
            logger.error(f"Error deactivating card: {e}")
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message=str(e),
                    error_type="ServerError"
                )
            )

@router.get('/readers')
async def list_readers():
    """Lists available smart card readers."""
    try:
        readers = detect_readers()
        return standard_response(
            message="Available readers retrieved successfully",
            data={"readers": readers}
        )
    except Exception as e:
        logger.error(f"Error listing readers: {e}")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message=str(e),
                error_type="ServerError"
            )
        )
