"""Configuration settings for the Bluetooth chat application."""

# Application information
APP_NAME = "Simple Bluetooth Chat"
APP_VERSION = "1.0.0"

# UI settings
UI_WIDTH = 800
UI_HEIGHT = 600
UI_BG_COLOR = "#f0f0f0"
UI_TEXT_COLOR = "#000000"
UI_SEND_BG = "#e3f2fd"

# Bluetooth settings
BT_PORT = 1  # RFCOMM port for Bluetooth
BUFFER_SIZE = 4096  # Message buffer size
ENCODING = 'utf-8'  # Text encoding

# Message protocol constants
MSG_PREFIX = "MSG:"
NAME_PREFIX = "NAME:"
FILE_PREFIX = "FILE:"
DISCONNECT_MSG = "DISCONNECT"

# Bluetooth settings
BT_SCAN_DURATION = 10  # seconds
BT_SERVICE_UUID = "94f39d29-7d6d-437d-973b-fba39e49d4ee"  # Unique service UUID
BT_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Characteristic UUID

# Data settings
MAX_MESSAGE_SIZE = 1024  # Maximum message size in bytes

# File transfer settings
CHUNK_SIZE = 4096  # Size of chunks when sending files
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB max file size

# Timeouts
CONNECTION_TIMEOUT = 10  # seconds
SCAN_TIMEOUT = 15  # seconds

# UI settings
UI_MIN_WIDTH = 600
UI_MIN_HEIGHT = 400
UI_PADDING = 10 