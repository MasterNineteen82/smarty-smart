"""
Deployment script for Smart Card Manager
Helps set up and deploy the application in different environments
"""

import os
import sys
import argparse
import shutil
import json
import subprocess
from pathlib import Path

def create_env_file(env_type, host, port, log_level, admin_key):
    """Create environment file for deployment"""
    env_vars = {
        'SMARTY_ENV': env_type,
        'SMARTY_HOST': host,
        'SMARTY_PORT': port,
        'SMARTY_LOG_LEVEL': log_level,
        'SMARTY_ADMIN_KEY': admin_key or 'change-me-in-production',
        'SMARTY_SECRET_KEY': os.urandom(24).hex(),
    }
    
    if env_type == 'production':
        # Add production-specific settings
        env_vars['SMARTY_PIN_KEY'] = os.urandom(16).hex()
    
    filename = '.env'
    with open(filename, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"Created environment file: {filename}")
    return filename

def create_systemd_service(name, user, path):
    """Create systemd service file for Linux deployment"""
    service_content = f"""[Unit]
Description=Smart Card Manager Service
After=network.target

[Service]
User={user}
WorkingDirectory={path}
ExecStart=/usr/bin/python3 {path}/smart.py
Restart=always
Environment=PYTHONUNBUFFERED=1
EnvironmentFile={path}/.env

[Install]
WantedBy=multi-user.target
"""
    
    filename = f"{name}.service"
    with open(filename, 'w') as f:
        f.write(service_content)
    
    print(f"Created systemd service file: {filename}")
    print(f"To install, copy to /etc/systemd/system/ and run: sudo systemctl enable {name}")
    return filename

def create_windows_service(name, path):
    """Create Windows service configuration"""
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import socket
    
    nssm_cmd = f"nssm install {name} python {path}\\smart.py"
    print(f"To install as a Windows service, you can use NSSM with this command:")
    print(nssm_cmd)
    print(f"Or run this Python command: python -m pip install pywin32 && python {path}\\win_service.py install")
    
    # Create win_service.py file
    service_content = """import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import subprocess
import logging
from pathlib import Path

class SmartCardService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SmartCardManager"
    _svc_display_name_ = "Smart Card Manager Service"
    _svc_description_ = "Manages smart card lifecycle operations"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = False
        
        # Set up logging
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'win_service.log')
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('smartcard_service')

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        self.logger.info("Service is stopping...")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.is_running = True
        self.logger.info("Service is starting...")
        
        # Start the Smart Card Manager
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart.py')
            self.process = subprocess.Popen([sys.executable, script_path])
            self.logger.info(f"Started smart.py with PID {self.process.pid}")
            
            # Wait for stop signal
            while self.is_running:
                rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop signal received
                    break
            
            # Terminate the process
            if self.process:
                self.process.terminate()
                self.logger.info("Terminated smart.py process")
        except Exception as e:
            self.logger.error(f"Error running service: {e}")
            servicemanager.LogErrorMsg(f"Error running service: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SmartCardService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SmartCardService)
"""
    
    with open('win_service.py', 'w') as f:
        f.write(service_content)
    
    print("Created Windows service script: win_service.py")
    return 'win_service.py'

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy Smart Card Manager")
    
    parser.add_argument(
        "--env", 
        choices=["development", "testing", "production"],
        default="development",
        help="Deployment environment"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--admin-key",
        help="Admin key for secured operations"
    )
    
    parser.add_argument(
        "--service-name",
        default="smartcard-manager",
        help="Service name for system service installation"
    )
    
    parser.add_argument(
        "--service-user",
        default=os.environ.get("USER", "nobody"),
        help="User to run the service as (Linux only, default: current user)"
    )
    
    args = parser.parse_args()
    
    # Create environment file
    env_file = create_env_file(
        args.env,
        args.host,
        args.port,
        args.log_level,
        args.admin_key
    )
    
    # Create service files based on platform
    if os.name == 'nt':  # Windows
        service_file = create_windows_service(
            args.service_name,
            os.path.abspath(os.path.dirname(__file__))
        )
    else:  # Linux/Mac
        service_file = create_systemd_service(
            args.service_name,
            args.service_user,
            os.path.abspath(os.path.dirname(__file__))
        )
    
    print("\nDeployment files created successfully!")
    print(f"Environment: {args.env}")
    print(f"Host: {args.host}:{args.port}")
    
    if args.env == "production":
        print("\nPRODUCTION DEPLOYMENT CHECKLIST:")
        print("1. Set secure admin key and secret key in .env file")
        print("2. Configure proper logging")
        print("3. Set up a reverse proxy (Nginx/Apache) for HTTPS")
        print("4. Install as a system service for automatic startup")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())