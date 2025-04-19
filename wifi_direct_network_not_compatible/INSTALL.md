# Installation Guide for Offline Network

This guide will help you set up and run the Offline Network application, which allows direct communication between laptops using WiFi Direct without requiring internet connectivity.

## Prerequisites

- Python 3.8 or higher
- A WiFi adapter that supports WiFi Direct (most modern laptops have this)
- Windows, macOS, or Linux operating system

## Installation Steps

1. **Clone or download the repository**

   Download the code to your local machine.

2. **Set up a Python virtual environment (optional but recommended)**

   ```bash
   # Create a virtual environment
   python -m venv venv

   # Activate the virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the required dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Note: The `pywifi` library requires additional setup on some platforms:

   - **Windows**: No additional steps required.
   - **macOS**: You may need to install additional libraries. Refer to the [pywifi documentation](https://github.com/awkman/pywifi).
   - **Linux**: You'll need to install the `python3-dev` package and the wireless development libraries:
     ```bash
     sudo apt-get update
     sudo apt-get install python3-dev libffi-dev libssl-dev
     sudo apt-get install wireless-tools libcap-dev iw
     ```

## Running the Application

1. **Run the application**

   ```bash
   python run.py
   ```

   For more verbose logging, use:

   ```bash
   python run.py --log-level DEBUG
   ```

2. **Using the application**

   - To create a new network, enter a network name, your username, and click "Create Network"
   - To join an existing network, enter the same network name used by the creator, your username, and click "Join Network"
   - Once connected, you can send messages and files to other connected users

## Troubleshooting

- **WiFi Direct not working**: Ensure your WiFi adapter supports WiFi Direct and that it's enabled in your system settings
- **Connection issues**: Make sure all devices are using the same network name
- **Installation errors**: If you encounter issues installing dependencies, try updating pip (`pip install --upgrade pip`) before installation
- **Permission issues on Linux**: You might need to run the application with sudo or adjust your system permissions to allow manipulating WiFi interfaces

## Additional Notes

- The application creates a direct peer-to-peer connection, so all devices need to be within WiFi range of each other (typically 30-100 feet indoors)
- WiFi Direct creates its own network, so you may temporarily lose internet connectivity on the device while using the application
- For best performance, keep devices relatively close to each other 