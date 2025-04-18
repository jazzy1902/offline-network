import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional

from src.network.message import Message, MessageType
from src.network.manager import NetworkManager

logger = logging.getLogger("OfflineNetwork.UI")

class MainWindow:
    """Main window for the offline network application."""
    
    def __init__(self, network_manager: NetworkManager, test_mode: bool = False):
        """Initialize the main window.
        
        Args:
            network_manager: Network manager instance
            test_mode: Whether to run in test mode (no actual WiFi connections)
        """
        self.network_manager = network_manager
        self.test_mode = test_mode
        
        # Register message handlers
        self.network_manager.register_handler(MessageType.CHAT, self._handle_chat_message)
        self.network_manager.register_handler(MessageType.FILE_TRANSFER_REQUEST, self._handle_file_request)
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Offline Network" + (" (TEST MODE)" if test_mode else ""))
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Create frames
        self._create_connection_frame()
        self._create_chat_frame()
        self._create_peers_frame()
        
        # Start UI update timer
        self.root.after(1000, self._update_ui)

    def _create_connection_frame(self) -> None:
        """Create the connection control frame."""
        frame = ttk.LabelFrame(self.root, text="Connection")
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Network name input
        ttk.Label(frame, text="Network Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.network_name_var = tk.StringVar(value="OfflineNetwork")
        ttk.Entry(frame, textvariable=self.network_name_var).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Username input
        ttk.Label(frame, text="Your Name:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.username_var = tk.StringVar(value=self.network_manager.user_name)
        ttk.Entry(frame, textvariable=self.username_var).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Connection buttons
        frame_buttons = ttk.Frame(frame)
        frame_buttons.grid(row=1, column=0, columnspan=4, pady=5)
        
        self.create_button = ttk.Button(frame_buttons, text="Create Network", command=self._create_network)
        self.create_button.pack(side=tk.LEFT, padx=5)
        
        self.join_button = ttk.Button(frame_buttons, text="Join Network", command=self._join_network)
        self.join_button.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_button = ttk.Button(frame_buttons, text="Disconnect", command=self._disconnect)
        self.disconnect_button.pack(side=tk.LEFT, padx=5)
        self.disconnect_button.config(state=tk.DISABLED)
        
        # Status label
        self.status_var = tk.StringVar(value="Disconnected" + (" (TEST MODE)" if self.test_mode else ""))
        status_label = ttk.Label(frame, textvariable=self.status_var)
        status_label.grid(row=2, column=0, columnspan=4, pady=5)

    def _create_chat_frame(self) -> None:
        """Create the chat frame."""
        frame = ttk.LabelFrame(self.root, text="Chat")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Chat history
        self.chat_history = tk.Text(frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message input
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self._send_message)
        
        send_button = ttk.Button(input_frame, text="Send", command=self._send_message)
        send_button.pack(side=tk.LEFT, padx=5)
        
        # File transfer
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        send_file_button = ttk.Button(file_frame, text="Send File", command=self._send_file)
        send_file_button.pack(side=tk.LEFT, padx=5)

    def _create_peers_frame(self) -> None:
        """Create the peers list frame."""
        frame = ttk.LabelFrame(self.root, text="Connected Peers")
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Peer list
        self.peer_list = ttk.Treeview(
            frame, 
            columns=("name", "address"),
            show="headings",
            height=5
        )
        self.peer_list.heading("name", text="Name")
        self.peer_list.heading("address", text="Address")
        self.peer_list.column("name", width=150)
        self.peer_list.column("address", width=150)
        self.peer_list.pack(fill=tk.X, padx=5, pady=5)
        
        # Refresh button
        refresh_button = ttk.Button(frame, text="Refresh", command=self._refresh_peers)
        refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Discover peers button
        discover_button = ttk.Button(frame, text="Discover Peers", command=self._discover_peers)
        discover_button.pack(side=tk.LEFT, padx=5, pady=5)

    def _update_ui(self) -> None:
        """Update the UI with current network state."""
        # Update connection status
        if self.network_manager.is_running:
            info = self.network_manager.get_connection_info()
            status = f"Connected as {'group owner' if info['is_group_owner'] else 'client'}"
            status += f" | Network: {info['network_name']}"
            status += f" | IP: {info['local_ip']}"
            status += f" | Peers: {info['peer_count']}"
            self.status_var.set(status)
            
            # Update button states
            self.create_button.config(state=tk.DISABLED)
            self.join_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            
            # Refresh peer list occasionally
            self._refresh_peers()
        else:
            self.status_var.set("Disconnected")
            self.create_button.config(state=tk.NORMAL)
            self.join_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
        
        # Schedule next update
        self.root.after(5000, self._update_ui)

    def _create_network(self) -> None:
        """Create a new WiFi Direct network."""
        # Update user name
        self.network_manager.user_name = self.username_var.get()
        
        # Update network name
        self.network_manager.wifi_direct.network_name = self.network_name_var.get()
        
        # Start network
        if self.network_manager.start(as_group_owner=True, test_mode=self.test_mode):
            self._append_to_chat("System", "Created network and waiting for peers to connect.")
        else:
            messagebox.showerror("Error", "Failed to create network")

    def _join_network(self) -> None:
        """Join an existing WiFi Direct network."""
        # Update user name
        self.network_manager.user_name = self.username_var.get()
        
        # Update network name
        self.network_manager.wifi_direct.network_name = self.network_name_var.get()
        
        # Start network
        if self.network_manager.start(as_group_owner=False, test_mode=self.test_mode):
            self._append_to_chat("System", "Joined network and discovering peers.")
        else:
            messagebox.showerror("Error", "Failed to join network")

    def _disconnect(self) -> None:
        """Disconnect from the network."""
        self.network_manager.stop()
        self._append_to_chat("System", "Disconnected from network.")

    def _send_message(self, event=None) -> None:
        """Send a chat message."""
        message = self.message_entry.get().strip()
        if not message:
            return
        
        if not self.network_manager.is_running:
            messagebox.showwarning("Not Connected", "You must be connected to a network to send messages.")
            return
        
        if self.network_manager.send_chat_message(message):
            # Add message to chat history
            self._append_to_chat(f"You ({self.network_manager.user_name})", message)
            
            # Clear message entry
            self.message_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Error", "Failed to send message. No peers connected.")

    def _send_file(self) -> None:
        """Send a file to all peers."""
        if not self.network_manager.is_running:
            messagebox.showwarning("Not Connected", "You must be connected to a network to send files.")
            return
        
        # Open file dialog
        filepath = filedialog.askopenfilename(
            title="Select File to Send",
            filetypes=(("All Files", "*.*"),)
        )
        
        if not filepath:
            return
        
        try:
            file_id = self.network_manager.send_file(filepath)
            filename = os.path.basename(filepath)
            self._append_to_chat("System", f"Sending file: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file: {e}")

    def _refresh_peers(self) -> None:
        """Refresh the peer list."""
        # Clear current list
        for item in self.peer_list.get_children():
            self.peer_list.delete(item)
        
        # Add peers
        peers = self.network_manager.get_connected_peers()
        for addr, name in peers:
            self.peer_list.insert("", tk.END, values=(name, addr))

    def _discover_peers(self) -> None:
        """Discover peers on the network."""
        if not self.network_manager.is_running:
            messagebox.showwarning("Not Connected", "You must be connected to a network to discover peers.")
            return
        
        self.network_manager.discover_peers()
        self._append_to_chat("System", "Discovering peers...")

    def _handle_chat_message(self, message: Message) -> None:
        """Handle incoming chat messages.
        
        Args:
            message: Chat message
        """
        self._append_to_chat(message.sender_name, message.content)

    def _handle_file_request(self, message: Message) -> None:
        """Handle incoming file transfer requests.
        
        Args:
            message: File transfer request message
        """
        filename = message.content['filename']
        file_size = message.content['file_size']
        file_id = message.content['file_id']
        sender = message.sender_name
        
        self._append_to_chat("System", f"{sender} wants to send file: {filename} ({file_size} bytes)")
        
        # Ask user if they want to accept
        if messagebox.askyesno("File Transfer", 
                              f"{sender} wants to send you a file:\n\n"
                              f"Filename: {filename}\n"
                              f"Size: {file_size} bytes\n\n"
                              "Do you want to accept?"):
            
            # Get save location
            save_path = filedialog.asksaveasfilename(
                title="Save File As",
                initialfile=filename,
                filetypes=(("All Files", "*.*"),)
            )
            
            if save_path:
                self.network_manager.accept_file(file_id, save_path)
                self._append_to_chat("System", f"Accepted file: {filename}")
            else:
                self.network_manager.reject_file(file_id)
                self._append_to_chat("System", f"Cancelled file transfer: {filename}")
        else:
            self.network_manager.reject_file(file_id)
            self._append_to_chat("System", f"Rejected file: {filename}")

    def _append_to_chat(self, sender: str, message: str) -> None:
        """Append a message to the chat history.
        
        Args:
            sender: Name of the sender
            message: Message text
        """
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{sender}: {message}\n")
        self.chat_history.see(tk.END)
        self.chat_history.config(state=tk.DISABLED)

    def _on_close(self) -> None:
        """Handle window close event."""
        if self.network_manager.is_running:
            self.network_manager.stop()
        self.root.destroy()

    def run(self) -> None:
        """Run the main window."""
        self.root.mainloop() 