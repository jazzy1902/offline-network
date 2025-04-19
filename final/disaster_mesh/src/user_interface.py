import os
import time
import threading
import datetime
import json
try:
    # When running as a module
    from disaster_mesh.src.network import DisasterMeshNode
except ImportError:
    # When running directly
    from src.network import DisasterMeshNode

class DisasterMeshUI:
    def __init__(self):
        self.node = DisasterMeshNode()
        self.node.set_logger(self.log)
        self.running = False
        self.messages = []
        self.username = None
        
    def log(self, message):
        """Custom logger for mesh network events."""
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def start(self):
        """Start the user interface."""
        self.running = True
        self.clear_screen()
        self.print_header()
        
        # Get username
        while not self.username:
            username = input("Enter your name/handle: ").strip()
            if username:
                self.username = username
        
        # Start the mesh network
        if not self.node.start():
            print("Failed to start mesh network. Please check your network connection.")
            return
        
        # Start UI update thread
        threading.Thread(target=self._ui_updater, daemon=True).start()
        
        try:
            self._main_loop()
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the user interface and network."""
        self.running = False
        self.node.stop()
        print("\nDisaster Mesh application stopped. Stay safe!")
            
    def _main_loop(self):
        """Main command loop for user input."""
        self.help()
        
        while self.running:
            command = input("> ").strip().lower()
            
            if command == "exit" or command == "quit":
                self.stop()
                break
                
            elif command == "help":
                self.help()
                
            elif command == "peers":
                self.list_peers()
                
            elif command == "messages":
                self.show_messages()
                
            elif command.startswith("send "):
                message = command[5:].strip()
                if message:
                    self.send_message(message)
                else:
                    print("Message cannot be empty.")
                    
            elif command == "clear":
                self.clear_screen()
                self.print_header()
                
            elif command == "status":
                self.show_status()
                
            elif command == "whoami":
                print(f"You are: {self.username} (Node ID: {self.node.node_id})")
                
            else:
                print("Unknown command. Type 'help' for available commands.")
    
    def _ui_updater(self):
        """Background thread to update the UI with new messages."""
        last_message_count = 0
        while self.running:
            current_messages = self.node.get_messages()
            
            # Check if there are new messages
            if len(current_messages) > last_message_count:
                # Get only new messages
                new_messages = current_messages[:len(current_messages) - last_message_count]
                for message in reversed(new_messages):
                    if message["sender"] != self.node.node_id:  # Don't show our own messages again
                        time_str = self._format_timestamp(message["timestamp"])
                        sender = message["sender"]
                        content = message["content"]
                        print(f"\n[{time_str}] {sender}: {content}")
                        print("> ", end="", flush=True)  # Restore prompt
                
                last_message_count = len(current_messages)
            
            # Check for new peers
            # TODO: Announce when new peers join the network
            
            time.sleep(2)
    
    def send_message(self, message):
        """Send a message to the mesh network."""
        formatted_message = {
            "type": "chat",
            "username": self.username,
            "text": message
        }
        self.node.send_message(formatted_message)
        print(f"Message sent: {message}")
    
    def list_peers(self):
        """List all connected peers."""
        if not self.node.peers:
            print("No peers connected.")
            return
            
        print(f"\n=== Connected Peers ({len(self.node.peers)}) ===")
        now = time.time()
        
        for peer_id, (ip, last_seen) in self.node.peers.items():
            age = now - last_seen
            if age < 60:
                status = "Active"
            elif age < 300:
                status = "Idle"
            else:
                status = "Inactive"
                
            print(f"- {peer_id} ({ip}) - {status} - Last seen: {int(age)} seconds ago")
    
    def show_messages(self):
        """Show recent messages."""
        messages = self.node.get_messages()
        if not messages:
            print("No messages yet.")
            return
            
        print(f"\n=== Recent Messages ({len(messages)}) ===")
        
        for message in messages:
            time_str = self._format_timestamp(message["timestamp"])
            content = message["content"]
            
            if isinstance(content, dict) and content.get("type") == "chat":
                sender = content.get("username", "Unknown")
                text = content.get("text", "")
                print(f"[{time_str}] {sender}: {text}")
            else:
                sender = message["sender"]
                print(f"[{time_str}] {sender}: {content}")
    
    def show_status(self):
        """Show current status of the mesh network."""
        print("\n=== Disaster Mesh Status ===")
        print(f"Your ID: {self.node.node_id}")
        print(f"Username: {self.username}")
        print(f"Connected peers: {len(self.node.peers)}")
        print(f"Messages stored: {len(self.node.messages)}")
        
        ip = self.node._get_local_ip()
        print(f"Your IP address: {ip or 'Unknown'}")
        print(f"Running: {self.node.running}")
    
    def help(self):
        """Show available commands."""
        print("\n=== Available Commands ===")
        print("help      - Show this help")
        print("send [msg] - Send a message to all peers")
        print("messages  - Show recent messages")
        print("peers     - List connected peers")
        print("status    - Show network status")
        print("whoami    - Show your identity")
        print("clear     - Clear the screen")
        print("exit      - Exit the application")
    
    def print_header(self):
        """Print application header."""
        print("=" * 60)
        print("          D I S A S T E R   M E S H   N E T W O R K")
        print("=" * 60)
        print("A mesh networking application for disaster scenarios")
        print("Stay connected even when traditional networks fail.")
        print("=" * 60)
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _format_timestamp(self, timestamp_str):
        """Format an ISO timestamp string to a readable time."""
        try:
            dt = datetime.datetime.fromisoformat(timestamp_str)
            return dt.strftime("%H:%M:%S")
        except:
            return "??:??:??"

if __name__ == "__main__":
    ui = DisasterMeshUI()
    ui.start() 