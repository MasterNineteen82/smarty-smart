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

from card_utils import (
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
            raise HTTPException(status_code=400, detail=error_response("ValueError", str(e)))
        except KeyError as e:
            logger.warning(f"Key error: {e}")
            raise HTTPException(status_code=400, detail=error_response("KeyError", str(e)))
        except CardConnectionException as e:
            logger.error(f"Card connection error: {e}")
            raise HTTPException(status_code=500, detail=error_response("CardConnectionError", str(e), "Check card and reader"))
        except Exception as e:
            logger.exception(f"Operation failed: {e}")
            suggestion = None
            if "No card present" in str(e):
                suggestion = "Please place a card on the reader"
            elif "Connection failed" in str(e):
                suggestion = "Check if reader is properly connected"
            raise HTTPException(status_code=500, detail=error_response(e.__class__.__name__, str(e), suggestion))
    return decorated_function

def error_response(error_type, error_details, suggestion=None):
    response = {
        "status": "error",
        "message": f"Operation failed: {error_details}",
        "error_type": error_type,
        "error_details": error_details,
        "timestamp": datetime.datetime.now().isoformat()
    }
    if suggestion:
        response["suggestion"] = suggestion
    return response

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
        return {"status": status, "readers": readers_str}
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        raise HTTPException(status_code=500, detail="Error rendering index page")

@router.post('/start_server', endpoint='start_server')
@log_operation_timing("Start Server")
@handle_card_exceptions
async def start_server_route():
    try:
        # from app.app import app # no flask app
        # run_server(app) # no flask app
        return {"message": "Server start not implemented", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise HTTPException(status_code=500, detail=error_response("ServerStartError", str(e)))

@router.post('/card_status', endpoint='card_status')
@log_operation_timing("Card Status")
@handle_card_exceptions
async def get_card_status():
    try:
        # Use device_manager to detect readers
        reader_list = detect_readers()
        if not reader_list:
            raise HTTPException(status_code=400, detail={"status": "warning", "message": "No readers detected"})

        reader = str(reader_list[0])
        conn, err = establish_connection(reader)
        if err:
            raise HTTPException(status_code=400, detail={"status": "error", "message": f"Card not present: {err}"})

        atr = toHexString(conn.getATR())
        card_type = detect_card_type(atr)
        close_connection(conn)
        return {
            "status": "success",
            "message": f"Card Status: ACTIVE\nATR: {atr}",
            "card_type": card_type
        }
    except Exception as e:
        logger.error(f"Error getting card status: {e}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": "An error occurred"})

@router.post('/stop_server', endpoint='stop_server')
@log_operation_timing("Stop Server")
@handle_card_exceptions
async def stop_server_route():
    try:
        # stop_server() # no flask app
        return {"message": "Server stop not implemented", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to stop server: {e}")
        raise HTTPException(status_code=500, detail=error_response("ServerStopError", str(e)))

@router.post('/connect', endpoint='connect_card')
@log_operation_timing("Connect Card")
@handle_card_exceptions
async def connect_card():
    reader_list = [str(r) for r in readers()]
    if not reader_list:
        raise HTTPException(status_code=400, detail={"status": "warning", "message": "No readers detected"})

    results = []
    for r in reader_list:
        conn, err = establish_connection(r)
        results.append({"reader": r, "success": conn is not None, "message": err or "Connected successfully"})
        if conn:
            close_connection(conn)

    return {"status": "success", "results": results}

@router.post('/read_memory', endpoint='read_memory')
@log_operation_timing("Read Memory")
async def read_memory():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        try:
            apdu = [0xFF, 0xB0, 0x00, 0x00, 0x100]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
                output = f"HEX: {hex_data}\nASCII: {ascii_data}"
                return {"message": output, "status": "success"}
            raise HTTPException(status_code=500, detail={"message": f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})
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
            raise HTTPException(status_code=403, detail={"message": "Card blocked: Too many PIN attempts", "status": "error"})

        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})

        try:
            pin = request.pin or DEFAULT_PIN
            if not isinstance(pin, str) or len(pin) != 3 or not pin.isdigit():
                raise HTTPException(status_code=400, detail={"message": "PIN must be a 3-digit number", "status": "error"})

            # Use security_manager to verify PIN
            if security_manager.verify_pin(pin):
                pin_attempts = 0
                return {"message": "PIN verified", "status": "success"}
            else:
                pin_attempts += 1
                remaining = MAX_PIN_ATTEMPTS - pin_attempts
                msg = f"PIN failed: {remaining} attempts left"
                if pin_attempts >= MAX_PIN_ATTEMPTS:
                    card_status = CardStatus.BLOCKED
                    msg += " Card blocked."
                raise HTTPException(status_code=401, detail={"message": msg, "status": "error"})
        finally:
            close_connection(conn)

class UpdatePinRequest(BaseModel):
    pin: str

@router.post('/update_pin', endpoint='update_pin')
async def update_pin(request: UpdatePinRequest):
    global pin_attempts, card_status
    with safe_globals():
        if pin_attempts >= MAX_PIN_ATTEMPTS:
            raise HTTPException(status_code=403, detail={"message": "Card blocked", "status": "error"})
        
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        
        try:
            new_pin = request.pin
            if not isinstance(new_pin, str) or len(new_pin) != 3 or not new_pin.isdigit():
                raise HTTPException(status_code=400, detail={"message": "New PIN must be a 3-digit number", "status": "error"})
            
            verify_apdu = [0xFF, 0x20, 0x00, 0x00, 0x03, 0x31, 0x32, 0x33]
            _, sw1, sw2 = conn.transmit(verify_apdu)
            if sw1 != 0x90 or sw2 != 0x00:
                pin_attempts += 1
                raise HTTPException(status_code=401, detail={"message": f"Current PIN verification failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})
            
            pin_bytes = [ord(c) for c in new_pin]
            apdu = [0xFF, 0xD0, 0x00, 0x00, 0x03] + pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                pin_attempts = 0
                return {"message": "PIN updated", "status": "success"}
            raise HTTPException(status_code=500, detail={"message": f"Update failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})
        finally:
            close_connection(conn)

@router.get('/card_info', endpoint='card_info')
@log_operation_timing("Get Card Info")
@handle_card_exceptions
async def card_info_route():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={
                "message": json.dumps({
                    "status": "No card",
                    "error": err
                }),
                "status": "warning"
            })
        
        try:
            atr = toHexString(conn.getATR())
            card_type = "Unknown" # card_info.get("card_type", "Unknown") # card_info is not defined
            reader_type = detect_reader_type(selected_reader.name)

            extra_info = {}
            
            if card_type == "MIFARE_CLASSIC":
                try:
                    pass
                except Exception:
                    pass
            
            registered = is_card_registered(atr)
            
            info = {
                "atr": atr,
                "card_type": card_type,
                "reader_type": reader_type,
                "protocol": "Unknown", # card_info.get("protocol", "Unknown"), # card_info is not defined
                "card_status": card_status.name,
                "registered": registered,
                "extra": extra_info
            }
            
            return {
                "message": json.dumps(info),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error getting card info: {e}")
            raise HTTPException(status_code=500, detail={
                "message": f"Error getting card info: {e}",
                "status": "error"
            })
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
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        
        try:
            offset = request.offset
            length = request.length
            if offset < 0 or length < 1 or offset + length > 256:
                raise HTTPException(status_code=400, detail={"message": "Invalid offset or length", "status": "error"})
            
            apdu = [0xFF, 0xB0, offset >> 8, offset & 0xFF, length]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                return {"message": hex_data, "status": "success"}
            raise HTTPException(status_code=500, detail={"message": f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})
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
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        
        try:
            offset = request.offset
            data_hex = request.data.replace(' ', '')
            if offset < 0 or not all(c in '0123456789ABCDEFabcdef' for c in data_hex):
                raise HTTPException(status_code=400, detail={"message": "Invalid offset or data", "status": "error"})
            
            data_bytes = toBytes(data_hex)
            if offset + len(data_bytes) > 256:
                raise HTTPException(status_code=400, detail={"message": "Data exceeds card capacity", "status": "error"})
            
            apdu = [0xFF, 0xD6, offset >> 8, offset & 0xFF, len(data_bytes)] + list(data_bytes)
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                return {"message": "Write successful", "status": "success"}
            raise HTTPException(status_code=500, detail={"message": f"Write failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})
        finally:
            close_connection(conn)

@router.post('/change_pin', endpoint='change_pin')
@log_operation_timing("Change PIN")
async def change_pin():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        
        try:
            raise HTTPException(status_code=501, detail={"message": "Not implemented", "status": "error"})
        finally:
            close_connection(conn)

@router.get('/card_status', endpoint='get_card_status')
@log_operation_timing("Get Card Status")
@handle_card_exceptions
async def card_status_get():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})
        
        try:
            raise HTTPException(status_code=501, detail={"message": "Not implemented", "status": "error"})
        except Exception as e:
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})
        finally:
            close_connection(conn)

@router.post('/format_card', endpoint='format_card')
@log_operation_timing("Format Card")
@handle_card_exceptions
async def format_card():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})

        try:
            format_apdu = [0xFF, 0x00, 0x00, 0x00, 0x00]
            data, sw1, sw2 = conn.transmit(format_apdu)

            if sw1 == 0x90 and sw2 == 0x00:
                return {"message": "Card formatted successfully", "status": "success"}
            else:
                raise HTTPException(status_code=500, detail={"message": f"Format failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"})

        except Exception as e:
            logger.error(f"Error formatting card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})
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
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})

        try:
            atr = request.atr
            if not atr:
                raise HTTPException(status_code=400, detail={"message": "ATR is required", "status": "error"})

            # Use CardLifecycleManager to block the card
            success, message, _ = card_lifecycle_manager.block_existing_card(atr)
            if success:
                return {"message": message, "status": "success"}
            else:
                raise HTTPException(status_code=500, detail={"message": message, "status": "error"})

        except Exception as e:
            logger.error(f"Error blocking card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})
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
            raise HTTPException(status_code=400, detail={"message": err, "status": "error"})

        try:
            atr = toHexString(conn.getATR())
            user_id = request.user_id

            if not user_id:
                raise HTTPException(status_code=400, detail={"message": "User ID is required", "status": "error"})

            # Use CardLifecycleManager to register the card
            success, message = card_lifecycle_manager.register_new_card(atr, user_id)
            if success:
                return {"message": message, "status": "success"}
            else:
                raise HTTPException(status_code=500, detail={"message": message, "status": "error"})

        except CardError as e:
            logger.error(f"Error registering card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})
        except Exception as e:
            logger.error(f"Error registering card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})
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
            raise HTTPException(status_code=400, detail={"message": "ATR is required", "status": "error"})
        try:
            # Use CardLifecycleManager to unregister the card
            # success, message = card_lifecycle_manager.unregister_existing_card(atr)
            # if success:
            #     return {"message": message, "status": "success"})
            # else:
            #     return {"message": message, "status": "error"})
            raise HTTPException(status_code=501, detail={"message": "Not implemented", "status": "error"})
        except Exception as e:
            logger.error(f"Error unregistering card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})

@router.get('/check_registration', endpoint='check_registration')
@log_operation_timing("Check Card Registration")
@handle_card_exceptions
async def check_registration(atr: str):
    if not atr:
        raise HTTPException(status_code=400, detail={"message": "ATR is required", "status": "error"})
    try:
        is_registered = card_manager.is_card_registered(atr)
        return {"is_registered": is_registered, "status": "success"}
    except Exception as e:
        logger.error(f"Error checking card registration: {e}")
        raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})

class CardActionRequest(BaseModel):
    atr: str

@router.post('/activate_card', endpoint='activate_card')
@log_operation_timing("Activate Card")
@handle_card_exceptions
async def activate_card(request: CardActionRequest):
    with safe_globals():
        atr = request.atr
        if not atr:
            raise HTTPException(status_code=400, detail={"message": "ATR is required", "status": "error"})
        try:
            # Use CardLifecycleManager to activate the card
            success, message, _ = card_lifecycle_manager.activate_existing_card(atr)
            if success:
                return {"message": message, "status": "success"}
            else:
                raise HTTPException(status_code=500, detail={"message": message, "status": "error"})
        except Exception as e:
            logger.error(f"Error activating card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})

@router.post('/deactivate_card', endpoint='deactivate_card')
@log_operation_timing("Deactivate Card")
@handle_card_exceptions
async def deactivate_card(request: CardActionRequest):
    with safe_globals():
        atr = request.atr
        if not atr:
            raise HTTPException(status_code=400, detail={"message": "ATR is required", "status": "error"})
        try:
            # Use CardLifecycleManager to deactivate the card
            success, message, _ = card_lifecycle_manager.deactivate_existing_card(atr)
            if success:
                return {"message": message, "status": "success"}
            else:
                raise HTTPException(status_code=500, detail={"message": message, "status": "error"})
        except Exception as e:
            logger.error(f"Error deactivating card: {e}")
            raise HTTPException(status_code=500, detail={"message": str(e), "status": "error"})

@router.get('/readers')
async def list_readers():
    """Lists available smart card readers."""
    try:
        readers = detect_readers()
        return readers
    except Exception as e:
        logger.error(f"Error listing readers: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Example of how to include the router in a FastAPI app
app = FastAPI()
app.include_router(router)