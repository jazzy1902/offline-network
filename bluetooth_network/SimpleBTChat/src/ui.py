"""User interface for Bluetooth chat application."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from typing import Callable, Optional, List, Dict, Any

from .config import UI_BG_COLOR, UI_TEXT_COLOR, UI_SEND_BG, UI_WIDTH, UI_HEIGHT


class ChatUI:
    """User interface for Bluetooth chat application."""
    
    def __init__(self, 
                 send_message_callback: Callable[[str], None],
                 send_file_callback: Callable[[str], None],
                 connect_callback: Callable[[str], None],
                 start_server_callback: Callable[[], None],
                 scan_devices_callback: Callable[[], None],
                 disconnect_callback: Callable[[], None]):
        """Initialize the UI.
        
        Args:
            send_message_callback: Callback for sending text messages
            send_file_callback: Callback for sending files
            connect_callback: Callback for connecting to a device
            start_server_callback: Callback for starting server mode
            scan_devices_callback: Callback for scanning for devices
            disconnect_callback: Callback for disconnecting
        """
        self.send_message_callback = send_message_callback
        self.send_file_callback = send_file_callback
        self.connect_callback = connect_callback
        self.start_server_callback = start_server_callback
        self.scan_devices_callback = scan_devices_callback
        self.disconnect_callback = disconnect_callback
        
        self.root = tk.Tk()
        self.root.title("Bluetooth Chat")
        self.root.geometry(f"{UI_WIDTH}x{UI_HEIGHT}")
        self.root.configure(bg=UI_BG_COLOR)
        
        self.username = "User"  # Default username
        self.is_connected = False
        self.devices = []  # List of discovered devices
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface elements."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection frame (left)
        conn_frame = ttk.LabelFrame(main_frame, text="Connection")
        conn_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Username input
        ttk.Label(conn_frame, text="Your Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_entry = ttk.Entry(conn_frame, width=15)
        self.username_entry.insert(0, self.username)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Server mode button
        self.server_btn = ttk.Button(conn_frame, text="Start Server", command=self._start_server)
        self.server_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Scan for devices button
        self.scan_btn = ttk.Button(conn_frame, text="Scan for Devices", command=self._scan_devices)
        self.scan_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Device list
        ttk.Label(conn_frame, text="Available Devices:").grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5)
        self.device_listbox = tk.Listbox(conn_frame, height=10, width=25)
        self.device_listbox.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky=tk.NSEW)
        self.device_listbox.bind("<Double-1>", self._connect_to_selected)
        
        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self._connect_to_selected)
        self.connect_btn.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Status indicator
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(conn_frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        
        # Disconnect button
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self._disconnect, state=tk.DISABLED)
        self.disconnect_btn.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        # Chat frame (right)
        chat_frame = ttk.LabelFrame(main_frame, text="Chat")
        chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat history
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED, 
                                                     bg=UI_BG_COLOR, fg=UI_TEXT_COLOR)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message input
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", self._send_message)
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side=tk.RIGHT)
        
        # File transfer button
        self.file_btn = ttk.Button(chat_frame, text="Send File", command=self._select_file)
        self.file_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Initial state
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Update UI elements based on connection state."""
        if self.is_connected:
            self.status_var.set("Connected")
            self.status_label.config(foreground="green")
            self.server_btn.config(state=tk.DISABLED)
            self.scan_btn.config(state=tk.DISABLED)
            self.connect_btn.config(state=tk.DISABLED)
            self.device_listbox.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.message_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.file_btn.config(state=tk.NORMAL)
        else:
            self.status_var.set("Disconnected")
            self.status_label.config(foreground="red")
            self.server_btn.config(state=tk.NORMAL)
            self.scan_btn.config(state=tk.NORMAL)
            self.connect_btn.config(state=tk.NORMAL)
            self.device_listbox.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.message_entry.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.DISABLED)
            self.file_btn.config(state=tk.DISABLED)
    
    def _start_server(self):
        """Start server mode."""
        self.username = self.username_entry.get().strip() or "User"
        try:
            self.start_server_callback()
            self.show_info_message("Server mode started")
            # Don't set connected state until someone connects
        except Exception as e:
            self.show_error_message(f"Failed to start server: {str(e)}")
    
    def _scan_devices(self):
        """Scan for Bluetooth devices."""
        self.device_listbox.delete(0, tk.END)
        try:
            self.scan_devices_callback()
            self.show_info_message("Scanning for devices...")
        except Exception as e:
            self.show_error_message(f"Failed to scan: {str(e)}")
    
    def _connect_to_selected(self, event=None):
        """Connect to the selected device."""
        self.username = self.username_entry.get().strip() or "User"
        if not self.devices:
            self.show_error_message("No devices available")
            return
            
        selection = self.device_listbox.curselection()
        if not selection:
            self.show_error_message("Please select a device first")
            return
            
        index = selection[0]
        if index < len(self.devices):
            device = self.devices[index]
            try:
                self.connect_callback(device["addr"])
                # Connection status will be updated by set_connected method
            except Exception as e:
                self.show_error_message(f"Failed to connect: {str(e)}")
    
    def _disconnect(self):
        """Disconnect from the current connection."""
        try:
            self.disconnect_callback()
            self.set_disconnected()
        except Exception as e:
            self.show_error_message(f"Error during disconnect: {str(e)}")
    
    def _send_message(self, event=None):
        """Send a text message."""
        message = self.message_entry.get().strip()
        if not message:
            return
            
        if not self.is_connected:
            self.show_error_message("Not connected")
            return
            
        try:
            self.send_message_callback(message)
            # Display own message
            self.display_message(self.username, message)
            self.message_entry.delete(0, tk.END)
        except Exception as e:
            self.show_error_message(f"Failed to send message: {str(e)}")
    
    def _select_file(self):
        """Select a file to send."""
        if not self.is_connected:
            self.show_error_message("Not connected")
            return
            
        filepath = filedialog.askopenfilename(
            title="Select File to Send",
            filetypes=[("All Files", "*.*")]
        )
        
        if not filepath:
            return  # User cancelled
            
        try:
            self.send_file_callback(filepath)
            filename = os.path.basename(filepath)
            self.display_system_message(f"Sending file: {filename}")
        except Exception as e:
            self.show_error_message(f"Failed to send file: {str(e)}")
    
    def set_connected(self, peer_name: str = "Peer"):
        """Set the connection state to connected.
        
        Args:
            peer_name: Name of the connected peer
        """
        self.is_connected = True
        self._update_ui_state()
        self.display_system_message(f"Connected to {peer_name}")
    
    def set_disconnected(self):
        """Set the connection state to disconnected."""
        self.is_connected = False
        self._update_ui_state()
        self.display_system_message("Disconnected")
    
    def update_device_list(self, devices: List[Dict[str, Any]]):
        """Update the list of available devices.
        
        Args:
            devices: List of device dictionaries with 'name' and 'addr'
        """
        self.devices = devices
        self.device_listbox.delete(0, tk.END)
        
        if not devices:
            self.device_listbox.insert(tk.END, "No devices found")
        else:
            for device in devices:
                self.device_listbox.insert(tk.END, device.get("name", "Unknown") + 
                                           f" ({device.get('addr', 'N/A')})")
    
    def display_message(self, sender: str, message: str):
        """Display a chat message.
        
        Args:
            sender: Name of the message sender
            message: Message content
        """
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: {message}\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def display_system_message(self, message: str):
        """Display a system message in the chat.
        
        Args:
            message: System message content
        """
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"--- {message} ---\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def show_error_message(self, message: str):
        """Show an error message dialog.
        
        Args:
            message: Error message to display
        """
        messagebox.showerror("Error", message)
    
    def show_info_message(self, message: str):
        """Show an information message dialog.
        
        Args:
            message: Information message to display
        """
        messagebox.showinfo("Information", message)
    
    def start(self):
        """Start the UI main loop."""
        self.root.mainloop()
    
    def quit(self):
        """Quit the application."""
        self.root.quit()
        self.root.destroy() 