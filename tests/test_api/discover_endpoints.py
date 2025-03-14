import aiohttp
import asyncio
import json
import logging
from colorama import Fore, Style, init
import os
from urllib.parse import urljoin
from datetime import datetime

# Initialize colorama
init()

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Set up logging with timestamped log file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f'discover_endpoints_{timestamp}.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

def print_color(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")
    logging.info(text)

async def test_endpoint(session, base_url, path):
    """Test if an endpoint exists and return its response"""
    url = urljoin(base_url, path)
    print_color(f"Testing: {url}", Fore.CYAN)
    
    try:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            status = response.status
            print_color(f"Status: {status}", Fore.GREEN)
            
            try:
                data = await response.json()
                print_color("Response:", Fore.GREEN)
                response_text = json.dumps(data, indent=2)
                print(response_text)
                logging.info(response_text)
            except json.JSONDecodeError:
                response_text = f"Response (text): {await response.text()[:100]}"
                print_color(response_text, Fore.YELLOW)
                logging.info(response_text)
            
            return True
    except aiohttp.ClientResponseError as http_err:
        print_color(f"HTTP error occurred: {http_err}", Fore.RED)
        logging.error(f"HTTP error occurred: {http_err}")
    except aiohttp.ClientConnectionError as conn_err:
        print_color(f"Connection error occurred: {conn_err}", Fore.RED)
        logging.error(f"Connection error occurred: {conn_err}")
    except asyncio.TimeoutError as timeout_err:
        print_color(f"Timeout error occurred: {timeout_err}", Fore.RED)
        logging.error(f"Timeout error occurred: {timeout_err}")
    except aiohttp.ClientError as req_err:
        print_color(f"Request error occurred: {req_err}", Fore.RED)
        logging.error(f"Request error occurred: {req_err}")
    except Exception as e:
        print_color(f"An error occurred: {str(e)}", Fore.RED)
        logging.error(f"An error occurred: {str(e)}")
    
    return False

async def discover_api_structure(base_url="http://localhost:5000"):
    """Try common API paths to discover structure"""
    print_color("=== DISCOVERING API STRUCTURE ===", Fore.MAGENTA)
    print_color(f"Base URL: {base_url}", Fore.CYAN)
    
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        print_color("Invalid base URL. Must start with http:// or https://", Fore.RED)
        logging.error("Invalid base URL. Must start with http:// or https://")
        return
    
    # Common API paths to check
    paths = [
        "/",                  # Root
        "/api",               # API root
        "/docs",              # FastAPI docs
        "/openapi.json",      # OpenAPI spec
        "/health",            # Health check
        "/status",            # Status
        "/v1",                # Version prefix
        "/api/v1",            # API with version
        "/api/card",          # Card endpoint
        "/api/cards",         # Cards collection
        "/cards",             # Alternative cards path
        "/readers",           # Readers
        "/api/readers",       # API readers
        
        # Smart card specific paths
        "/card",
        "/card/status",
        "/reader",
        "/reader/status",
        "/reader/list",
        "/smartcard",
        "/smartcard/status",
        
        # Try without /api prefix (based on previous results)
        "/connect",
        "/verify_pin",
        "/read_memory",
        "/write_memory",
        "/format",
    ]
    
    working_paths = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [test_endpoint(session, base_url, path) for path in paths]
        results = await asyncio.gather(*tasks)
        
        for path, result in zip(paths, results):
            if result:
                working_paths.append(path)
    
    print_color("\n=== DISCOVERY RESULTS ===", Fore.MAGENTA)
    if working_paths:
        print_color("Working endpoints found:", Fore.GREEN)
        for path in working_paths:
            print_color(f"  ✓ {path}", Fore.GREEN)
    else:
        print_color("No working endpoints found!", Fore.RED)

if __name__ == "__main__":
    asyncio.run(discover_api_structure())