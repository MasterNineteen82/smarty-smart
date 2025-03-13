# Smart Card Manager

A comprehensive lifecycle management system for smart cards and NFC/RFID tags, with support for Cherry SmartTerminal ST, ACR122U readers, and other PC/SC compliant devices.

## Features

- **Card Connection & Discovery**
  - Auto-detection of connected readers
  - Connection to NFC/RFID cards with configurable timeouts
  - Support for multiple concurrent readers

- **Card Identification**
  - Automatic detection of card type and protocol
  - Support for MIFARE Classic, Ultralight, DESFire, FeliCa, ISO cards
  - Card UID/NUID extraction and validation

- **Lifecycle Management**
  - Registration with customizable metadata
  - Activation/deactivation workflows with audit trail
  - Block/unblock mechanisms with admin override
  - Expiration management with configurable alerts

- **Data Security**
  - End-to-end encryption of stored card data
  - Secure memory operations (read/write)
  - PIN management with retry counters
  - Secure deletion and disposal options

- **Administrative Functions**
  - Backup & restore of card data with encryption
  - Batch operations for multiple cards
  - Recovery mode with elevated privileges
  - Detailed audit logging

## Supported Hardware

### Readers

| Reader Model | Connection Type | Compatibility Level | Notes |
|--------------|-----------------|---------------------|-------|
| Cherry SmartTerminal ST | USB/Serial | Full | Preferred for security operations |
| ACS ACR122U | USB | Full | Best for general NFC operations |
| Generic PC/SC readers | USB/Serial | Partial | Feature availability varies |

### Card Types

| Card Family | Supported Types | Read Support | Write Support |
|-------------|-----------------|--------------|---------------|
| MIFARE Classic | 1K, 4K | Full | Full |
| MIFARE Ultralight | All variants | Full | Full |
| MIFARE DESFire | EV1, EV2, EV3 | Full | Partial |
| FeliCa | Standard, Lite | Full | Partial |
| ISO 14443 | Type A/B | Full | Varies by card |
| NFC Forum | Type 1-4 | Full | Type 1-4 |

## Installation

### Prerequisites

- **System Requirements**:
  - Python 3.8+
  - 100MB disk space
  - Admin privileges for driver installation

- **Required Software**:
  - PC/SC middleware:
    - Windows: WinSCard (built-in)
    - Linux: PCSC-Lite (`sudo apt-get install pcscd libpcsclite-dev`)
    - macOS: PCSC-Lite (built-in)
  - Reader-specific drivers

### Installation Methods

#### Using pip (Recommended)

```bash
pip install smart-card-manager
```

#### From Source

1. Clone the repository:

     ```bash
     git clone https://github.com/username/smart-card-manager.git
     cd smart-card-manager
     ```

2. Install dependencies:

     ```bash
     pip install -r requirements.txt
     ```

3. Install the package:

     ```bash
     pip install -e .
     ```

## Quick Start Guide

1. Connect your smart card reader to your computer
2. Launch the Smart Card Manager:

     ```bash
     smartcard-mgr
     ```

3. The application will auto-detect available readers
4. Place a card on the reader to begin operations

## Configuration

Configuration settings are stored in `config.yaml`. Key settings include:

```yaml
readers:
    preferred: "ACS ACR122U"
    connection_timeout: 5  # seconds
    
security:
    encryption_method: "AES-256"
    pin_retry_limit: 3
    
logging:
    level: "INFO"
    file: "smartcard.log"
```

The Smart Card Manager uses a centralized configuration system in `config.py`. You can customize the application behavior using:

1. Environment variables (recommended for production)
2. JSON configuration files
3. Direct modification of `config.py` (not recommended)

### Key Configuration Options

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Environment | SMARTY_ENV | development | Application environment (development, testing, production) |
| Host | SMARTY_HOST | localhost | Server host address |
| Port | SMARTY_PORT | 5000 | Server port |
| Admin Key | SMARTY_ADMIN_KEY | admin123 | Admin access key (change in production!) |
| Log Level | SMARTY_LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| Default Reader | SMARTY_DEFAULT_READER | | Auto-select this reader on startup |

### Reader-Specific Configuration

The application includes optimized settings for specific readers:

- **Cherry SmartTerminal ST**: Longer timeouts, full NFC support
- **ACR122U**: Adjusted timeouts, limited FeliCa support

## Deployment

A deployment script is provided to help set up the application in various environments:

```bash
# Development deployment (default)
python deploy.py

# Production deployment
python deploy.py --env production --host 0.0.0.0 --port 8080 --log-level WARNING --admin-key your-secure-key

# Testing environment
python deploy.py --env testing --port 5001
```

## Troubleshooting

| Problem | Possible Causes | Solution |
|---------|----------------|----------|
| Reader not detected | Driver not installed | Install manufacturer drivers |
| | PC/SC service not running | Start PC/SC service |
| Card not detected | Card placement incorrect | Ensure proper positioning |
| | Incompatible card type | Check supported cards list |
| Write operation fails | Card write-protected | Check card permissions |
| | Insufficient privileges | Run as administrator |

## Documentation

Comprehensive documentation is available at [https://smartcard-manager.docs.io](https://smartcard-manager.docs.io)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
