import asyncio
import aiohttp
import logging
import sys
import os
from datetime import datetime
import pandas as pd
from colorama import init, Fore, Style

# Initialize colorama
init()

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Set up logging to both file and console
LOG_FILE = os.path.join(LOG_DIR, f"api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class ApiTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.session = None
        logger.info(f"Initializing API tester for {base_url}")
    
    def log_header(self, text):
        """Print a header with magenta color"""
        logger.info(f"{Fore.MAGENTA}{text}{Style.RESET_ALL}")
    
    def log_info(self, text):
        """Print info with cyan color"""
        logger.info(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    
    def log_success(self, text):
        """Print success message with green color"""
        logger.info(f"{Fore.GREEN}{text}{Style.RESET_ALL}")
    
    def log_warning(self, text):
        """Print warning with yellow color"""
        logger.info(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")
    
    def log_error(self, text):
        """Print error with red color"""
        logger.error(f"{Fore.RED}{text}{Style.RESET_ALL}")
    
    async def test_endpoint(self, endpoint, method="GET", body=None, description=""):
        """Test an API endpoint for standard response format"""
        self.log_header("\n=====================================")
        self.log_info(f"Testing: {description}")
        self.log_info(f"{method} {self.base_url}{endpoint}")
        
        # Initialize result object
        result = {
            "Endpoint": endpoint,
            "Method": method,
            "Description": description,
            "Success": False,
            "HasStandardFormat": False,
            "Status": "unknown",
            "Message": "",
            "HasData": False
        }
        
        try:
            # Prepare request
            url = f"{self.base_url}{endpoint}"
            kwargs = {"timeout": 10}
            
            if method != "GET" and body:
                kwargs["json"] = body
                self.log_info(f"Request body: {body}")
            
            # Make request
            async with self.session.request(method, url, **kwargs) as response:
                # Log full response details
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {dict(response.headers)}")
                response_text = await response.text()
                logger.info(f"Response content: {response_text}")
                
                self.log_success("Response received:")
                print(response_text[:500])  # Print first 500 chars
                
                # Parse response
                try:
                    data = await response.json()
                    
                    # Update result with success info
                    result["Success"] = True
                    
                    # Check for standard format
                    has_status = "status" in data
                    has_message = "message" in data
                    has_data = "data" in data
                    
                    result["HasStandardFormat"] = has_status and has_message
                    result["Status"] = data.get("status", "N/A")
                    result["Message"] = data.get("message", "N/A")
                    result["HasData"] = has_data
                    
                    # Display format check results
                    if result["HasStandardFormat"]:
                        self.log_success("✓ PASS: Response has standard format (status and message)")
                        
                        if result["Status"] in ["success", "error"]:
                            self.log_success(f"✓ PASS: Status value is standardized ({result['Status']})")
                        else:
                            self.log_error(f"✗ FAIL: Status value is non-standard ({result['Status']})")
                            result["HasStandardFormat"] = False
                        
                        if has_data:
                            self.log_success("✓ PASS: Data field is present")
                    else:
                        self.log_error("✗ FAIL: Response is missing required fields")
                        if not has_status:
                            self.log_error("  - Missing 'status' field")
                        if not has_message:
                            self.log_error("  - Missing 'message' field")
                    
                except ValueError:
                    self.log_error("Could not parse response as JSON")
                    result["HasStandardFormat"] = False
                    result["Success"] = False
                    result["Message"] = "Invalid JSON response"
        
        except asyncio.TimeoutError:
            self.log_error("Request timed out")
            result["Success"] = False
            result["Message"] = "Request timed out"
        
        except aiohttp.ClientConnectionError:
            self.log_error("Connection error occurred")
            result["Success"] = False
            result["Message"] = "Connection error"
        
        except aiohttp.ClientError as e:
            self.log_error(f"Request failed with HTTP error: {str(e)}")
            result["Success"] = False
            result["Message"] = str(e)
            
            # Try to parse error response if available
            if hasattr(e, "response") and e.response is not None:
                try:
                    logger.info(f"Error response text: {await e.response.text()}")
                    error_data = await e.response.json()
                    
                    # Check error format
                    has_status = "status" in error_data
                    has_message = "message" in error_data
                    has_suggestion = "suggestion" in error_data
                    
                    result["HasStandardFormat"] = has_status and has_message
                    result["Status"] = error_data.get("status", "N/A")
                    result["Message"] = error_data.get("message", "N/A")
                    
                    self.log_info("Error Response:")
                    print(await e.response.text()[:500])  # Print first 500 chars
                    
                    if result["HasStandardFormat"]:
                        self.log_success("✓ PASS: Error response has standard format")
                        
                        if has_suggestion:
                            self.log_success("✓ PASS: Error includes helpful suggestion")
                    else:
                        self.log_error("✗ FAIL: Error response is missing required fields")
                        if not has_status:
                            self.log_error("  - Missing 'status' field")
                        if not has_message:
                            self.log_error("  - Missing 'message' field")
                
                except ValueError:
                    self.log_error("Could not parse error response as JSON")
        
        # Add result to results list
        self.results.append(result)
        return result
    
    async def run_tests(self):
        """Run all API tests"""
        self.log_header("=================================================")
        self.log_header("SMART CARD MANAGER API STANDARDIZATION TEST")
        self.log_header("=================================================")
        self.log_info(f"Date: {datetime.now()}")
        self.log_info(f"Server: {self.base_url}")
        self.log_info(f"Log file: {LOG_FILE}")
        self.log_info("")  # Empty line for readability
        
        # Create a single session for all tests
        self.log_info("Creating HTTP session...")
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Test discovered endpoints
            self.log_header("\n--- Testing Existing API Endpoints ---")
            
            # Test /health (basic endpoint)
            await self.test_endpoint("/health", description="Health Check API")
            
            # Test /cards endpoints from OpenAPI spec
            await self.test_endpoint("/cards/status", description="Card Status API")
            
            # Register card endpoint (POST)
            card_data = {
                "atr": "test_atr_123",
                "user_id": 1,
                "status": "active",
                "id": 1
            }
            await self.test_endpoint(
                "/cards/register", 
                method="POST", 
                body=card_data,
                description="Register Card API"
            )
            
            # Test non-existent endpoint error handling
            self.log_header("\n--- Testing Error Handling ---")
            await self.test_endpoint("/nonexistent", description="Non-existent Endpoint")
            
            # Test card detail endpoints with path parameter
            # Format might vary based on real ATR values
            await self.test_endpoint(
                f"/cards/test_atr_123", 
                description="Get Card Details API"
            )
            
            # Display summary
            self.display_summary()
    
    def display_summary(self):
        """Display test results summary"""
        # Calculate statistics
        total_count = len(self.results)
        pass_count = sum(1 for r in self.results if r["HasStandardFormat"])
        pass_rate = int((pass_count / total_count) * 100) if total_count > 0 else 0
        
        self.log_header("\n=================================================")
        self.log_header("TEST RESULTS SUMMARY")
        self.log_header("=================================================")
        
        color = Fore.GREEN if pass_rate == 100 else Fore.YELLOW
        logger.info(f"{color}Tests with standard format: {pass_count} of {total_count} ({pass_rate}%){Style.RESET_ALL}")
        
        if pass_rate == 100:
            self.log_success("\nAll tested APIs follow the standardized format!")
        else:
            self.log_warning("\nSome APIs are not using the standardized format:")
            
            # Display failing endpoints
            failed = [r for r in self.results if not r["HasStandardFormat"]]
            for i, f in enumerate(failed, 1):
                self.log_warning(f"{i}. {f['Method']} {f['Endpoint']} - {f['Description']}")
            
            self.log_info("\nRecommendations:")
            self.log_info("1. Update these endpoints to use standard_response() and error_response() functions")
            self.log_info("2. Ensure all responses include 'status' and 'message' fields")
            self.log_info("3. Use 'success' or 'error' as the status value")
        
        # Save results to CSV
        self.save_results()
    
    def save_results(self):
        """Save test results to CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_test_results_{timestamp}.csv"
        
        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        self.log_info(f"\nDetailed results saved to {filename}")


if __name__ == "__main__":
    print(f"API Standardization Test Started - Log file: {LOG_FILE}")
    tester = ApiTester()
    asyncio.run(tester.run_tests())
    print(f"Testing complete. See {LOG_FILE} for full details.")