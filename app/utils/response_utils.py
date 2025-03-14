import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

def standard_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized successful response"""
    response = {
        "status": "success",
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

def error_response(message: str, error_type: Optional[str] = None, 
                  suggestion: Optional[str] = None) -> Dict[str, Any]:
    """Create a standardized error response"""
    response = {
        "status": "error",
        "message": message
    }
    if error_type:
        response["error_type"] = error_type
    if suggestion:
        response["suggestion"] = suggestion
    return response