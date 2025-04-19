# Offline Network

A peer-to-peer networking application that connects laptops directly using WiFi Direct without requiring internet connectivity or cellular networks.

## Overview

This project creates a direct device-to-device communication network using WiFi Direct technology. It enables users to communicate in environments where traditional internet infrastructure is unavailable or compromised, such as:

- Disaster-affected areas with damaged communication infrastructure
- Remote locations without cellular coverage
- Situations requiring secure, offline communications

## Features

- **Direct Connectivity**: Create and join WiFi Direct networks with no internet required
- **Peer Discovery**: Automatically find other devices on the network
- **Messaging**: Send and receive text messages in real-time
- **File Transfer**: Share files with other connected devices
- **User-Friendly Interface**: Simple GUI for all network operations

## Technology Stack

- **Python 3.8+**: Core programming language
- **pywifi**: Library for WiFi Direct functionality
- **socket**: Network communication
- **threading**: Concurrent operations
- **tkinter**: Graphical user interface

## Network Architecture

The application uses a hybrid peer-to-peer architecture:

1. **Group Owner Mode**: One device creates a WiFi Direct group and acts as a soft access point
2. **Client Mode**: Other devices connect to the group owner
3. **Direct Communication**: All devices can communicate directly with each other
4. **Auto-Discovery**: Automatic peer detection within the same network

## Computer Networks Concepts Applied

- **WiFi Direct (P2P)**: Enables direct device-to-device connections without an access point
- **TCP/IP Sockets**: Reliable data transmission between peers
- **Network Discovery**: Scanning and identifying peers on the network
- **Ad-hoc Networking**: Self-organizing network without centralized infrastructure
- **Reliable Data Transfer**: Chunked file transfers with verification
- **Message Protocol**: Structured communication format for different message types

## Project Structure

```
offline-network/
├── requirements.txt        # Python dependencies
├── run.py                  # Application entry point
├── INSTALL.md              # Installation instructions
├── README.md               # Project documentation
├── src/                    # Source code
│   ├── __init__.py
│   ├── app.py              # Main application
│   ├── network/            # Network functionality
│   │   ├── __init__.py
│   │   ├── wifi_direct.py  # WiFi Direct implementation
│   │   ├── message.py      # Message protocol
│   │   └── manager.py      # Network manager
│   ├── ui/                 # User interface
│   │   ├── __init__.py
│   │   └── main_window.py  # Main UI window
│   └── utils/              # Utility functions
│       ├── __init__.py
│       ├── file_transfer.py # File transfer utilities
│       └── network_utils.py # Network utilities
```

## Getting Started

See [INSTALL.md](INSTALL.md) for detailed installation and setup instructions.

### Quick Start

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python run.py
   ```

3. To create a network:
   - Enter a network name
   - Enter your username
   - Click "Create Network"

4. To join a network:
   - Enter the same network name used by the creator
   - Enter your username
   - Click "Join Network"

## Limitations and Future Work

Current limitations:
- WiFi Direct support varies across devices and operating systems
- Limited to devices within WiFi range (typically 30-100 feet indoors)
- No end-to-end encryption for messages (yet)

Future enhancements:
- End-to-end encryption for all communications
- Multi-hop message routing to extend network range
- Mobile application version for Android and iOS
- Mesh networking capabilities

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- This project was created as part of a Computer Networks course
- Thanks to the developers of the pywifi library
