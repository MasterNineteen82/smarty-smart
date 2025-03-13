import datetime
import time
import json
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import os

from flask import Blueprint, render_template, request, jsonify
from smartcard.System import readers
from smartcard.scard import SCARD_PRESENT, SCARD_STATE_PRESENT, SCARD_STATE_EMPTY

from card_utils import (
    safe_globals, status, card_status, CardStatus, pin_attempts, MAX_PIN_ATTEMPTS, logger,
    detect_card_type, is_card_registered, detect_reader_type
)

from server_utils import run_server, stop_server
from app.device_manager import detect_readers, get_device_info, configure_device, update_firmware, monitor_device_health
from app.core.card_manager import card_manager, CardError
from app.security_manager import security_manager
from app import get_models, get_api, get_core
from app.smart import logger

# Import pyscard modules
from smartcard.Exceptions import CardConnectionException
from smartcard.CardConnection import CardConnection
from smartcard.CardService import CardService
from smartcard.util import toHexString, toBytes

models = get_models()
core = get_core()

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
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Value error: {e}")
            return jsonify(error_response("ValueError", str(e))), 400
        except KeyError as e:
            logger.warning(f"Key error: {e}")
            return jsonify(error_response("KeyError", str(e))), 400
        except CardConnectionException as e:
            logger.error(f"Card connection error: {e}")
            return jsonify(error_response("CardConnectionError", str(e), "Check card and reader")), 500
        except Exception as e:
            logger.exception(f"Operation failed: {e}")
            suggestion = None
            if "No card present" in str(e):
                suggestion = "Please place a card on the reader"
            elif "Connection failed" in str(e):
                suggestion = "Check if reader is properly connected"
            return jsonify(error_response(e.__class__.__name__, str(e), suggestion)), 500
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
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting operation: {operation_name}")
            
            try:
                result = f(*args, **kwargs)
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

bp = Blueprint('routes', __name__)

def establish_connection(reader_name=None):
    try:
        if not reader_name:
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

@bp.route('/')
def index():
    try:
        readers = [str(r) for r in update_available_readers()]
        return render_template('index.html', status=status, readers=readers)
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return render_template('error.html', message="Error rendering index page"), 500

@bp.route('/start_server', methods=['POST'], endpoint='bp_start_server')
@log_operation_timing("Start Server")
@handle_card_exceptions
def start_server_route_bp():
    try:
        from app.app import app
        run_server(app)
        return jsonify({"message": "Server started", "status": "success"})
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return jsonify(error_response("ServerStartError", str(e))), 500

@bp.route('/card_status', methods=['POST'], endpoint='card_status')
@log_operation_timing("Card Status")
@handle_card_exceptions
def get_card_status():
    try:
        # Use device_manager to detect readers
        reader_list = detect_readers()
        if not reader_list:
            return jsonify({"status": "warning", "message": "No readers detected"})

        reader = str(reader_list[0])
        conn, err = establish_connection(reader)
        if err:
            return jsonify({"status": "error", "message": f"Card not present: {err}"})

        atr = toHexString(conn.getATR())
        card_type = detect_card_type(atr)
        close_connection(conn)
        return jsonify({
            "status": "success",
            "message": f"Card Status: ACTIVE\nATR: {atr}",
            "card_type": card_type
        })
    except Exception as e:
        logger.error(f"Error getting card status: {e}")
        return jsonify({"status": "error", "message": "An error occurred"})

@bp.route('/stop_server', methods=['POST'], endpoint='bp_stop_server')
@log_operation_timing("Stop Server")
@handle_card_exceptions
def stop_server_route():
    try:
        stop_server()
        return jsonify({"message": "Server stopped", "status": "success"})
    except Exception as e:
        logger.error(f"Failed to stop server: {e}")
        return jsonify(error_response("ServerStopError", str(e))), 500

@bp.route('/connect', methods=['POST'], endpoint='connect_card')
@log_operation_timing("Connect Card")
@handle_card_exceptions
def connect_card():
    reader_list = [str(r) for r in readers()]
    if not reader_list:
        return jsonify({"status": "warning", "message": "No readers detected"}), 200

    results = []
    for r in reader_list:
        conn, err = establish_connection(r)
        results.append({"reader": r, "success": conn is not None, "message": err or "Connected successfully"})
        if conn:
            close_connection(conn)

    return jsonify({"status": "success", "results": results})

@bp.route('/read_memory', methods=['POST'], endpoint='read_memory')
@log_operation_timing("Read Memory")
def read_memory():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        try:
            apdu = [0xFF, 0xB0, 0x00, 0x00, 0x100]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
                output = f"HEX: {hex_data}\nASCII: {ascii_data}"
                return jsonify({"message": output, "status": "success"})
            return jsonify({"message": f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/verify_pin', methods=['POST'], endpoint='verify_pin')
@log_operation_timing("Verify PIN")
def verify_pin():
    global pin_attempts, card_status
    with safe_globals():
        if pin_attempts >= MAX_PIN_ATTEMPTS:
            card_status = CardStatus.BLOCKED
            return jsonify({"message": "Card blocked: Too many PIN attempts", "status": "error"}), 403

        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400

        try:
            pin = request.json.get('pin', DEFAULT_PIN)
            if not isinstance(pin, str) or len(pin) != 3 or not pin.isdigit():
                return jsonify({"message": "PIN must be a 3-digit number", "status": "error"}), 400

            # Use security_manager to verify PIN
            if security_manager.verify_pin(pin):
                pin_attempts = 0
                return jsonify({"message": "PIN verified", "status": "success"})
            else:
                pin_attempts += 1
                remaining = MAX_PIN_ATTEMPTS - pin_attempts
                msg = f"PIN failed: {remaining} attempts left"
                if pin_attempts >= MAX_PIN_ATTEMPTS:
                    card_status = CardStatus.BLOCKED
                    msg += " Card blocked."
                return jsonify({"message": msg, "status": "error"}), 401
        finally:
            close_connection(conn)

@bp.route('/update_pin', methods=['POST'], endpoint='update_pin')
def update_pin():
    global pin_attempts, card_status
    with safe_globals():
        if pin_attempts >= MAX_PIN_ATTEMPTS:
            return jsonify({"message": "Card blocked", "status": "error"}), 403
        
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        
        try:
            new_pin = request.json.get('pin', '')
            if not isinstance(new_pin, str) or len(new_pin) != 3 or not new_pin.isdigit():
                return jsonify({"message": "New PIN must be a 3-digit number", "status": "error"}), 400
            
            verify_apdu = [0xFF, 0x20, 0x00, 0x00, 0x03, 0x31, 0x32, 0x33]
            _, sw1, sw2 = conn.transmit(verify_apdu)
            if sw1 != 0x90 or sw2 != 0x00:
                pin_attempts += 1
                return jsonify({"message": f"Current PIN verification failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 401
            
            pin_bytes = [ord(c) for c in new_pin]
            apdu = [0xFF, 0xD0, 0x00, 0x00, 0x03] + pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                pin_attempts = 0
                return jsonify({"message": "PIN updated", "status": "success"})
            return jsonify({"message": f"Update failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/card_info', methods=['GET'], endpoint='card_info')
@log_operation_timing("Get Card Info")
@handle_card_exceptions
def card_info_route():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({
                "message": json.dumps({
                    "status": "No card",
                    "error": err
                }),
                "status": "warning"
            })
        
        try:
            atr = toHexString(conn.getATR())
            card_type = card_info.get("card_type", "Unknown")
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
                "protocol": card_info.get("protocol", "Unknown"),
                "card_status": card_status.name,
                "registered": registered,
                "extra": extra_info
            }
            
            return jsonify({
                "message": json.dumps(info),
                "status": "success"
            })
        except Exception as e:
            logger.error(f"Error getting card info: {e}")
            return jsonify({
                "message": f"Error getting card info: {e}",
                "status": "error"
            }), 500
        finally:
            close_connection(conn)

@bp.route('/read_memory_region', methods=['POST'], endpoint='read_memory_region')
@log_operation_timing("Read Memory Region")
def read_memory_region():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        
        try:
            offset = int(request.json.get('offset', 0))
            length = int(request.json.get('length', 16))
            if offset < 0 or length < 1 or offset + length > 256:
                return jsonify({"message": "Invalid offset or length", "status": "error"}), 400
            
            apdu = [0xFF, 0xB0, offset >> 8, offset & 0xFF, length]
            data, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                hex_data = toHexString(data)
                return jsonify({"message": hex_data, "status": "success"})
            return jsonify({"message": f"Read failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/write_memory', methods=['POST'], endpoint='write_memory')
@log_operation_timing("Write Memory")
def write_memory():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        
        try:
            offset = int(request.json.get('offset', 0))
            data_hex = request.json.get('data', '').replace(' ', '')
            if offset < 0 or not all(c in '0123456789ABCDEFabcdef' for c in data_hex):
                return jsonify({"message": "Invalid offset or data", "status": "error"}), 400
            
            data_bytes = toBytes(data_hex)
            if offset + len(data_bytes) > 256:
                return jsonify({"message": "Data exceeds card capacity", "status": "error"}), 400
            
            apdu = [0xFF, 0xD6, offset >> 8, offset & 0xFF, len(data_bytes)] + list(data_bytes)
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                return jsonify({"message": "Write successful", "status": "success"})
            return jsonify({"message": f"Write failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/change_pin', methods=['POST'], endpoint='change_pin')
@log_operation_timing("Change PIN")
def change_pin():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        
        try:
            return jsonify({"message": "Not implemented", "status": "error"}), 501
        finally:
            close_connection(conn)

@bp.route('/card_status', methods=['GET'], endpoint='get_card_status')
@log_operation_timing("Get Card Status")
@handle_card_exceptions
def card_status_get():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400
        
        try:
            return jsonify({"message": "Not implemented", "status": "error"}), 501
        except Exception as e:
            return jsonify({"message": str(e), "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/format_card', methods=['POST'], endpoint='format_card')
@log_operation_timing("Format Card")
@handle_card_exceptions
def format_card():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400

        try:
            format_apdu = [0xFF, 0x00, 0x00, 0x00, 0x00]
            data, sw1, sw2 = conn.transmit(format_apdu)

            if sw1 == 0x90 and sw2 == 0x00:
                return jsonify({"message": "Card formatted successfully", "status": "success"})
            else:
                return jsonify({"message": f"Format failed: SW1={sw1:02X}, SW2={sw2:02X}", "status": "error"}), 500

        except Exception as e:
            logger.error(f"Error formatting card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/block_card_direct', methods=['POST'], endpoint='block_card_direct')
@log_operation_timing("Block Card (Direct)")
@handle_card_exceptions
def block_card_direct():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400

        try:
            atr = request.json.get('atr')
            if not atr:
                return jsonify({"message": "ATR is required", "status": "error"}), 400

            card_manager.block_card(atr)

            return jsonify({"message": "Card blocked successfully", "status": "success"})

        except Exception as e:
            logger.error(f"Error blocking card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/register_card', methods=['POST'], endpoint='register_card')
@log_operation_timing("Register Card")
@handle_card_exceptions
def register_card_route():
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return jsonify({"message": err, "status": "error"}), 400

        try:
            atr = toHexString(conn.getATR())
            user_id = request.json.get('user_id')

            if not user_id:
                return jsonify({"message": "User ID is required", "status": "error"}), 400

            card_manager.register_card(atr, user_id)

            return jsonify({"message": "Card registered successfully", "status": "success"})

        except CardError as e:
            logger.error(f"Error registering card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500
        except Exception as e:
            logger.error(f"Error registering card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500
        finally:
            close_connection(conn)

@bp.route('/unregister_card', methods=['POST'], endpoint='unregister_card')
@log_operation_timing("Unregister Card")
@handle_card_exceptions
def unregister_card():
    with safe_globals():
        atr = request.json.get('atr')
        if not atr:
            return jsonify({"message": "ATR is required", "status": "error"}), 400
        try:
            card_manager.unregister_card(atr)
            return jsonify({"message": "Card unregistered successfully", "status": "success"})
        except Exception as e:
            logger.error(f"Error unregistering card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500

@bp.route('/check_registration', methods=['GET'], endpoint='check_registration')
@log_operation_timing("Check Card Registration")
@handle_card_exceptions
def check_registration():
    atr = request.args.get('atr')
    if not atr:
        return jsonify({"message": "ATR is required", "status": "error"}), 400
    try:
        is_registered = card_manager.is_card_registered(atr)
        return jsonify({"is_registered": is_registered, "status": "success"})
    except Exception as e:
        logger.error(f"Error checking card registration: {e}")
        return jsonify({"message": str(e), "status": "error"}), 500

@bp.route('/activate_card', methods=['POST'], endpoint='activate_card')
@log_operation_timing("Activate Card")
@handle_card_exceptions
def activate_card():
    with safe_globals():
        atr = request.json.get('atr')
        if not atr:
            return jsonify({"message": "ATR is required", "status": "error"}), 400
        try:
            card_manager.activate_card(atr)
            return jsonify({"message": "Card activated successfully", "status": "success"})
        except Exception as e:
            logger.error(f"Error activating card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500

@bp.route('/deactivate_card', methods=['POST'], endpoint='deactivate_card')
@log_operation_timing("Deactivate Card")
@handle_card_exceptions
def deactivate_card():
    with safe_globals():
        atr = request.json.get('atr')
        if not atr:
            return jsonify({"message": "ATR is required", "status": "error"}), 400
        try:
            card_manager.deactivate_card(atr)
            return jsonify({"message": "Card deactivated successfully", "status": "success"})
        except Exception as e:
            logger.error(f"Error deactivating card: {e}")
            return jsonify({"message": str(e), "status": "error"}), 500

@bp.route('/readers', methods=['GET'])
def list_readers():
    """Lists available smart card readers."""
    try:
        readers = detect_readers()
        return jsonify(readers)
    except Exception as e:
        logger.error(f"Error listing readers: {e}")
        return jsonify({"error": str(e)}), 500
