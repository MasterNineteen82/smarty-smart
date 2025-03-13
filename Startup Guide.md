# SMART CARD MANAGER - STARTUP GUIDE

## Welcome to Smart Card Manager

Smart Card Manager is a comprehensive solution for managing smart card operations across multiple platforms. This guide will walk you through setup, configuration, and basic operations to help you get started quickly.

![Smart Card Manager Logo](assets/logo.png)

### What You Can Do With Smart Card Manager

- Read and write data to various smart card types
- Manage access control credentials
- Clone and duplicate compatible cards
- Format and initialize new cards
- Analyze card security features
- Automate card operations with scripts
- Generate detailed reports and logs

### Key Features

- **Cross-Platform Compatibility** - Works seamlessly across Windows, macOS, and Linux
- **Intuitive GUI** - Easy-to-navigate interface with dark and light themes
- **Comprehensive Card Support** - Compatible with major card technologies
- **Advanced Security** - Built-in encryption and secure key storage
- **Extensible Architecture** - API access for custom integrations
- **Detailed Logging** - Complete audit trail of all operations

### Getting Started

This guide will walk you through:

1. [Prerequisites](#prerequisites) - What you need before installation
2. [Installation](#installation) - Step-by-step setup process
3. [Configuration](#first-time-configuration) - Initial setup and customization
4. [Basic Operations](#quick-start-guide) - Essential day-to-day tasks
5. [Troubleshooting](#troubleshooting) - Solutions to common issues
6. [Advanced Usage](#advanced-configuration) - Taking your usage to the next level

Let's begin with ensuring your system meets all requirements.

## PREREQUISITES

This comprehensive guide will help you get started with the Smart Card Manager application quickly and efficiently. Follow these step-by-step instructions to ensure proper installation and operation.

### System Requirements

- **Operating Systems**:
  - Windows 10/11 (64-bit)
  - macOS 10.15 (Catalina) or higher
  - Linux: Ubuntu 20.04+, Debian 10+, Fedora 34+

- **Minimum Hardware**:
  - 4GB RAM (8GB recommended)
  - 200MB available disk space
  - One available USB port
  - 1280×720 screen resolution

### Software Requirements

#### Python 3.8 or higher

```bash
# Verify installation
python --version  # or python3 --version on Linux/macOS

# If needed, download from python.org
# Ensure "Add Python to PATH" is checked during Windows installation

# Verify pip is installed
pip --version
```

#### PC/SC Middleware

- **Windows**: WinSCard service (pre-installed)

    ```bash
    # Verify service is running
    sc query SCardSvr
    ```

- **Linux**: PCSC-Lite package

    ```bash
    # Install required packages
    sudo apt-get update
    sudo apt-get install pcscd libpcsclite-dev

    # Start and enable service
    sudo systemctl enable pcscd
    sudo systemctl start pcscd
    
    # Verify installation
    pcsc_scan
    ```

- **macOS**: PCSC-Lite (pre-installed)

    ```bash
    # Verify installation
    pcsc_scan
    ```

### Hardware Requirements

#### Compatible Smart Card Readers

- **Recommended Models**:
  - ACR122U NFC Reader - *Best for beginners, supports contactless*
  - Cherry SmartTerminal ST-1144 - *Reliable contact card reader*
  - HID OMNIKEY 5022 - *Enterprise-grade security*
  - Identiv uTrust 4701 F - *Compact form factor*
  - SCM SCR3500 - *High security applications*

- **Verify Connection**:
  - **Windows**: Device Manager → Smart Card Readers
  - **Linux**: `lsusb | grep -i 'card\|smartcard'`
  - **macOS**: System Information → USB

#### Compatible Smart Cards/Tags

- **Supported Technologies**:
  - ISO/IEC 7816 (contact cards)
  - ISO/IEC 14443 Type A/B (contactless)
  - MIFARE Classic (1K/4K)
  - MIFARE DESFire EV1/EV2
  - MIFARE Ultralight/Ultralight C
  - Java Cards (J2A040, J3A081, etc.)

- **Memory Requirements**:
  - Minimum: 1K for basic operations
  - Recommended: 4K for full functionality
  - Use blank or non-critical cards for testing

- **Starter Kit Recommendation**:
  - ACR122U reader + 5 MIFARE Classic 1K cards

## INSTALLATION

### 1. Obtain the Software

Clone the repository or download as a zip file:

```bash
# Option 1: Clone via git
git clone https://github.com/yourusername/smart-card-manager.git
cd smart-card-manager

# Option 2: Download zip (alternative)
# Visit https://github.com/yourusername/smart-card-manager
# Click "Code" > "Download ZIP"
# Extract to desired location and navigate to the folder
```

### 2. Set Up Virtual Environment (Recommended)

Creating a virtual environment prevents dependency conflicts with other Python projects:

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate

# Your terminal should now show (venv) at the beginning of the prompt
```

### 3. Install Dependencies

Install all required packages from the requirements file:

```bash
pip install -r requirements.txt

# Verify successful installation (no errors should appear):
pip list | grep -E 'pyscard|cryptography|pyDes|asn1crypto'
```

### 4. Verify Installation

Run the test suite to ensure all components are working correctly:

```bash
python -m smartcard.test

# Expected output:
# "Successfully connected to reader: [Your Reader Name]"
# "All tests passed successfully."
```

## FIRST-TIME CONFIGURATION

### 1. Run Initial Setup Wizard

The setup wizard will guide you through essential configuration steps:

```bash
python setup.py configure
```

Follow the on-screen prompts to:

- Select default reader
- Configure security parameters
- Set up logging preferences
- Create backup location

### 2. Configure Reader Settings

For detailed reader configuration:

1. Launch the application: `python smartcard_manager.py`
2. Navigate to the settings menu:
     - Click **Settings** > **Reader Configuration**
3. In the configuration panel:
     - Select your reader from the dropdown menu
     - Set communication protocol (T=0 or T=1)
     - Configure transmission speed (default: 9600 baud)
     - Set timeout values (recommended: 5-10 seconds)
4. Click **Test Connection** to verify settings
5. Save your configuration

### 3. User Preferences Setup

Configure application behavior:

1. Navigate to **Settings** > **User Preferences**
2. Customize:
     - UI theme (Light/Dark/System)
     - Auto-save interval (1-30 minutes)
     - Default save locations
     - Card data display format (HEX/ASCII/Decimal)

## QUICK START GUIDE

### 1. Launch the Application

```bash
# Make sure your virtual environment is activated, then:
python smartcard_manager.py

# For Windows users, you can also use the provided shortcut:
# Double-click SmartCardManager.bat
```

### 2. Connect Your Reader

1. Connect the reader to your computer before launching the application
2. Observe the status indicator in the bottom-right corner:
     - **Green**: Reader connected and ready
     - **Yellow**: Reader detected but not ready
     - **Red**: Reader not detected or error
3. If not connected, click **Devices** > **Refresh Connections**

### 3. Basic Operations

#### Reading Cards

1. Place card on reader
2. Click **Read Card** button or press **Ctrl+R**
3. Select reading mode:
     - **Basic**: General card info
     - **Standard**: Card data structure
     - **Advanced**: Full memory dump
4. View data in the main display panel

#### Writing to Cards

1. Enter data in the editor panel
2. Select write mode (Sector/Block/Application)
3. Click **Write Card** or press **Ctrl+W**
4. Confirm the write operation
5. Keep card on reader until "Write Complete" appears

#### Card Formatting

⚠️ **CAUTION**: Formatting erases ALL card data permanently!

1. Click **Tools** > **Format Card**
2. Select format type:
     - **Quick Format**: Clears directory only
     - **Full Format**: Erases all sectors
3. Enter administrator PIN if prompted
4. Confirm format intention
5. Keep card on reader until format completes

## TROUBLESHOOTING

## Smart Card & NFC/RFID Troubleshooting Flow

### 1. Reader Not Detected

- **Possible Causes:**
  - USB connection issue
  - Driver not installed
  - Incompatible reader
- **Resolution Steps:**
  - Check physical connection
  - Install the latest drivers from the manufacturer’s website
  - Verify the reader is on the compatibility list

---

### 2. Permission Denied

- **Possible Causes:**
  - Insufficient privileges
  - Service not running
- **Resolution Steps:**
  - Run as administrator (`sudo` on Linux)
  - Start the PC/SC service:
    - **Windows:** `sc start SCardSvr`
    - **Linux:** `sudo systemctl start pcscd`

---

### 3. Card Read Error

- **Possible Causes:**
  - Dirty card contacts
  - Card positioned incorrectly
  - Card damaged
- **Resolution Steps:**
  - Clean card contacts with isopropyl alcohol
  - Reposition the card according to reader markings
  - Try a different card for verification

---

### 4. Installation Errors

- **Possible Causes:**
  - Python version mismatch
  - Missing system dependencies
  - Network issues
- **Resolution Steps:**
  - Verify Python 3.8+ is installed
  - Install required system packages
  - Use `--no-index` with local packages

---

### 5. Write Operation Failed

- **Possible Causes:**
  - Card is read-only
  - Authentication failed
  - Insufficient privileges
- **Resolution Steps:**
  - Verify that the card is writable
  - Check key/PIN values
  - Use admin authentication

---

### 6. Slow Performance

- **Possible Causes:**
  - USB 1.0 port used
  - Resource conflicts
  - Debug mode enabled
- **Resolution Steps:**
  - Use a USB 2.0/3.0 port
  - Close competing applications
  - Disable verbose logging

## ADVANCED CONFIGURATION

### Custom Card Templates

Create templates for frequently used card types:

1. Navigate to **Tools** > **Template Manager**
2. Click **Create New Template**
3. Define:
     - Sector layouts
     - Data structures
     - Default values
4. Save template with descriptive name
5. Access from **Quick Templates** menu

### Scripting Operations

Automate repetitive tasks:

```python
# Example script (save as batch_read.py):
from smartcard_manager import CardReader, utils

reader = CardReader()
reader.connect()

cards = []
for i in range(5):
        input("Place card and press Enter...")
        card_data = reader.read_card()
        cards.append(card_data)
        print(f"Card {i+1} read successfully")

utils.export_data(cards, "batch_results.json")
print("All cards processed")
```

Run with: `python batch_read.py`

## ADDITIONAL RESOURCES

- **Documentation**: [Complete User Manual](https://smart-card-manager.docs.com)
- **Video Tutorials**: [Official YouTube Channel](https://youtube.com/smart-card-manager)
- **Community Forum**: [User Community](https://forum.smart-card-manager.com)
- **GitHub Repository**: [Source Code & Issues](https://github.com/yourusername/smart-card-manager)
- **API Reference**: [Developer Documentation](https://smart-card-manager.docs.com/api)

## SUPPORT CONTACT

For technical assistance:

- **Email**: <support@smart-card-manager.com>
- **Phone**: +1-555-SMARTCD (Mon-Fri, 9AM-5PM EST)
- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/smart-card-manager/issues)

---

## Version 2.3.0 | Last Updated: 2023-09-15
