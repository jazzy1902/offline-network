from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import os
import base64
import json

class MessageEncryption:
    def __init__(self, key=None):
        """Initialize with a key or generate a new one."""
        self.key = key or os.urandom(32)  # 256-bit key for AES
        
    def encrypt_message(self, message_dict):
        """Encrypt a message dictionary."""
        # Convert the message to JSON string
        message_json = json.dumps(message_dict)
        
        # Encrypt the message content
        iv = os.urandom(16)  # Generate a new IV for each message
        encrypted_content = self._encrypt_text(message_json, iv)
        
        # Create a new message with encrypted content
        encrypted_message = {
            'encrypted': True,
            'iv': base64.b64encode(iv).decode('utf-8'),
            'content': base64.b64encode(encrypted_content).decode('utf-8')
        }
        
        return encrypted_message
        
    def decrypt_message(self, encrypted_message):
        """Decrypt an encrypted message."""
        if not encrypted_message.get('encrypted', False):
            return encrypted_message  # Not encrypted
            
        # Get the IV and encrypted content
        iv = base64.b64decode(encrypted_message['iv'])
        encrypted_content = base64.b64decode(encrypted_message['content'])
        
        # Decrypt the content
        decrypted_json = self._decrypt_text(encrypted_content, iv)
        
        # Parse the JSON back to a dictionary
        return json.loads(decrypted_json)
        
    def _encrypt_text(self, text, iv):
        """Encrypt text using AES-CBC with PKCS7 padding."""
        # Create a padder for PKCS7 padding
        padder = padding.PKCS7(128).padder()
        
        # Pad the plaintext
        text_bytes = text.encode('utf-8')
        padded_data = padder.update(text_bytes) + padder.finalize()
        
        # Create an encryptor
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Encrypt the padded data
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return ciphertext
        
    def _decrypt_text(self, ciphertext, iv):
        """Decrypt ciphertext using AES-CBC with PKCS7 unpadding."""
        # Create a decryptor
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # Decrypt the ciphertext
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Create an unpadder for PKCS7 unpadding
        unpadder = padding.PKCS7(128).unpadder()
        
        # Unpad the decrypted data
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data.decode('utf-8')
        
    def export_key(self):
        """Export the encryption key as a base64 string."""
        return base64.b64encode(self.key).decode('utf-8')
        
    @classmethod
    def from_key(cls, key_base64):
        """Create an instance from a base64 encoded key."""
        key = base64.b64decode(key_base64)
        return cls(key=key) 