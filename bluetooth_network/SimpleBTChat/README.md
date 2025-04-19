# Simple Bluetooth Chat

A beginner-friendly Bluetooth chat application that allows two devices to connect and exchange messages wirelessly.

## Features

- Easy-to-use graphical interface
- Support for both host and client modes
- Automatic device discovery
- Text messaging between connected devices
- Connection status monitoring

## Requirements

- Python 3.7 or newer
- Windows 10 or 11 with Bluetooth capability
- Tkinter (included with standard Python installation)

## Installation

1. Make sure you have Python installed
2. Copy the `SimpleBTChat` folder to your computer
3. No external libraries required!

## How to Use

1. Run the application on both devices:
   ```
   python bluetooth_chat.py
   ```

2. On one device, select "Host" mode and click "Connect". This device will wait for incoming connections.

3. On the other device, select "Client" mode and:
   - Click "Scan for Devices" to find available Bluetooth devices
   - Double-click a device from the list (or manually enter the MAC address)
   - Click "Connect" to establish a connection

4. Once connected, the status will change to "Connected" and you can begin exchanging messages.

5. Type a message in the input box at the bottom and click "Send" or press Enter to send it.

6. To disconnect, click the "Disconnect" button.

## Troubleshooting

- **Bluetooth Not Working**: Ensure Bluetooth is enabled in your system settings
- **Can't Find Devices**: Try restarting Bluetooth on both devices and scan again
- **Connection Errors**: Make sure both devices have Bluetooth enabled and are within range
- **MAC Address Format**: Bluetooth MAC addresses should be in the format `XX:XX:XX:XX:XX:XX`

## Notes

- This is a simple implementation meant for educational purposes
- File transfer functionality is not implemented in this version
- For best results, ensure devices are paired in Windows Bluetooth settings first 