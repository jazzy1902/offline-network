import logging
import os
import base64
from typing import Tuple, Optional

logger = logging.getLogger("OfflineNetwork.FileTransfer")

def get_file_info(filepath: str) -> Tuple[str, int]:
    """Get information about a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Tuple[str, int]: Filename and file size in bytes
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    
    return filename, file_size

def read_file_chunk(filepath: str, chunk_number: int, chunk_size: int) -> Optional[bytes]:
    """Read a chunk of data from a file.
    
    Args:
        filepath: Path to the file
        chunk_number: Chunk number (0-based)
        chunk_size: Size of each chunk in bytes
        
    Returns:
        Optional[bytes]: Chunk data or None if chunk is out of range
    """
    try:
        file_size = os.path.getsize(filepath)
        start_pos = chunk_number * chunk_size
        
        if start_pos >= file_size:
            logger.warning(f"Chunk {chunk_number} is out of range for file {filepath}")
            return None
        
        with open(filepath, 'rb') as f:
            f.seek(start_pos)
            data = f.read(chunk_size)
            return data
            
    except Exception as e:
        logger.error(f"Error reading file chunk: {e}")
        return None

def write_file_chunk(filepath: str, chunk_number: int, chunk_size: int, data: bytes) -> bool:
    """Write a chunk of data to a file.
    
    Args:
        filepath: Path to the file
        chunk_number: Chunk number (0-based)
        chunk_size: Size of each chunk in bytes
        data: Chunk data
        
    Returns:
        bool: True if chunk written successfully
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Write chunk
        start_pos = chunk_number * chunk_size
        mode = 'r+b' if os.path.exists(filepath) else 'wb'
        
        with open(filepath, mode) as f:
            f.seek(start_pos)
            f.write(data)
        
        return True
            
    except Exception as e:
        logger.error(f"Error writing file chunk: {e}")
        return False

def encode_chunk(data: bytes) -> str:
    """Encode chunk data to base64 string.
    
    Args:
        data: Binary data
        
    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(data).decode('ascii')

def decode_chunk(encoded_data: str) -> bytes:
    """Decode base64 string to binary data.
    
    Args:
        encoded_data: Base64-encoded string
        
    Returns:
        bytes: Binary data
    """
    return base64.b64decode(encoded_data)

def calculate_chunks_count(file_size: int, chunk_size: int) -> int:
    """Calculate the number of chunks needed for a file.
    
    Args:
        file_size: Size of the file in bytes
        chunk_size: Size of each chunk in bytes
        
    Returns:
        int: Number of chunks
    """
    return (file_size + chunk_size - 1) // chunk_size  # Ceiling division 