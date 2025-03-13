import datetime
import time
import json
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, render_template, request, jsonify #Removed unused abort

from numpy import e
from smartcard.util import toHexString, toBytes
from smartcard.System import readers

from card_utils import (
    safe_globals, establish_connection, close_connection,
    status, card_status, CardStatus, pin_attempts, MAX_PIN_ATTEMPTS, logger,
    update_available_readers, selected_reader, card_info, detect_card_type, is_card_registered, detect_reader_type
)

from server_utils import run_server, stop_server
from card_manager import card_manager

# Add more comprehensive error handling decorator
def handle_card_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Value error: {e}")
            return jsonify({
                "status": "error",
                "message": f"Value error: {str(e)}",
                "error_type": "ValueError",
                "error_details": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
        except KeyError as e:
            logger.warning(f"Key error: {e}")
            return jsonify({
                "status": "error",
                "message": f"Key error: {str(e)}",
                "error_type": "KeyError",
                "error_details": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }), 400
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return jsonify({
                "status": "error",
                "message": f"Connection error: {str(e)}",
                "error_type": "ConnectionError",
                "error_details": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
                "suggestion": "Check if reader is properly connected"
            }), 500
        except Exception as e:
            logger.exception(f"Operation failed: {e}")
            error_response = {
                "status": "error",
                "message": f"Operation failed: {str(e)}",
                "error_type": e.__class__.__name__,
                "error_details": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
            if "No card present" in str(e):
                error_response["suggestion"] = "Please place a card on the reader"
            elif "Connection failed" in str(e):
                error_response["suggestion"] = "Check if reader is properly connected"
            return jsonify(error_response), 500
    return decorated_function

# Find the log_operation_timing decorator and update it to this:
def log_operation_timing(operation_name):
    """Decorator to log operation timing"""
    def decorator(f):
        @wraps(f)  # This is the critical line that preserves function metadata
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting operation: {operation_name}")
            
            try:
                result = f(*args, **kwargs)
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # ms
                logger.debug(f"Operation completed: {operation_name} in {duration:.2f}ms")
                return result
            except Exception as e:
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # ms
                logger.error(f"Operation failed: {operation_name} after {duration:.2f}ms - {e}")
                raise
            finally:
                logger.debug(f"Operation {operation_name} finished, total duration: {duration:.2f}ms")
                
        return wrapper
    return decorator

bp = Blueprint('routes', __name__)

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
    """Start the server route in blueprint"""
    try:
        # Import here to avoid circular import
        from smart import app
        run_server(app)  # Add app parameter here
        return jsonify({"message": "Server started", "status": "success"})
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return jsonify({
            "message": f"Failed to start server: {str(e)}",
            "status": "error",
            "error_type": e.__class__.__name__,
            "error_details": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# routes.py
routes = Blueprint('routes', __name__)

@bp.route('/card_status', methods=['POST'], endpoint='card_status')
@log_operation_timing("Card Status")
@handle_card_exceptions
def get_card_status():
    try:
        from smartcard.System import readers
        reader_list = readers()
        if not reader_list:
            return jsonify({"status": "warning", "message": "No readers detected"})
        
        reader = str(reader_list[0])  # Use first reader for simplicity
        conn, err = establish_connection(reader)
        if err:
            return jsonify({"status": "error", "message": f"Card not present: {err}"})
        
        atr = toHexString(conn.getATR())
        card_type = detect_card_type(atr)
        conn.disconnect()
        return jsonify({
            "status": "success",
            "message": f"Card Status: ACTIVE\nATR: {atr}",
            "card_type": card_type
        })
    except Exception:
        return jsonify({"status": "error", "message": "An error occurred"})

@bp.route('/stop_server', methods=['POST'], endpoint='bp_stop_server')
@log_operation_timing("Stop Server")
@handle_card_exceptions
def stop_server_route():
    """Stop the server route in blueprint"""
    try:
        stop_server()
        return jsonify({"message": "Server stopped", "status": "success"})
    except Exception as e:
        logger.error(f"Failed to stop server: {e}")
        return jsonify({
            "message": f"Failed to stop server: {str(e)}",
            "status": "error",
            "error_type": e.__class__.__name__,
            "error_details": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@bp.route('/connect', methods=['POST'], endpoint='connect_card')
@log_operation_timing("Connect Card")
@handle_card_exceptions
def connect_card():
    reader_list = [str(r) for r in readers()]
    if not reader_list:
        return jsonify({"status": "warning", "message": "No readers detected"}), 200

    with ThreadPoolExecutor(max_workers=len(reader_list)) as executor:
        future_to_reader = {executor.submit(establish_connection, r): r for r in reader_list}
        results = []
        for future in future_to_reader:
            conn, err = future.result()
            results.append({"reader": future_to_reader[future], "success": conn is not None, "message": err or "Connected successfully"})

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
            pin = request.json.get('pin', '123')
            if not isinstance(pin, str) or len(pin) != 3 or not pin.isdigit():
                return jsonify({"message": "PIN must be a 3-digit number", "status": "error"}), 400
            
            pin_bytes = [ord(c) for c in pin]
            apdu = [0xFF, 0x20, 0x00, 0x00, 0x03] + pin_bytes
            data, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                pin_attempts = 0
                return jsonify({"message": "PIN verified", "status": "success"})
            else:
                pin_attempts += 1
                remaining = MAX_PIN_ATTEMPTS - pin_attempts
                msg = f"PIN failed: SW1={sw1:02X}, SW2={sw2:02X}. {remaining} attempts left"
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
    """Get detailed information about the card"""
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
            reader_type = detect_reader_type(selected_reader.name) # Now in scope

            # Try to get additional info based on card type
            extra_info = {}
            
            if card_type == "MIFARE_CLASSIC":
                # Try to get MIFARE classic info (UID, etc)
                try:
                    pass
                except Exception:
                    pass
            
            # Check if card is registered
            registered = is_card_registered(atr) # Now in scope
            
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
        except Exception as e: #Remove unused variable
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
        except Exception: #Remove unused variable
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
            # Example: APDU command to format the card (replace with actual command)
            format_apdu = [0xFF, 0x00, 0x00, 0x00, 0x00]  # Placeholder
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

            # Call card_manager to block the card
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
            user_id = request.json.get('user_id')  # Get user ID from request

            if not user_id:
                return jsonify({"message": "User ID is required", "status": "error"}), 400

            card_manager.register_card(atr, user_id) # Use card_manager

            return jsonify({"message": "Card registered successfully", "status": "success"})

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