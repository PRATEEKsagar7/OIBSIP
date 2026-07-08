#!/usr/bin/env python3
"""
AuraChat - Multi-Room Real-Time Desktop Messaging Suite
Features:
- Dual-mode Startup Dialog: Runs both Server and Client roles in a single file
- Length-prefixed JSON Socket Protocol to prevent TCP packet splitting/merging
- Multi-client Threading: Supports multiple concurrent chat client socket channels
- User Profiles Database: SQLite registry storing PBKDF2-HMAC-SHA256 salted hashes
- Multi-room Chat Channels: Dynamic room joins/creates and instant broadcasts
- Message History: Persists chat transcripts in SQLite, re-loading upon rejoining a room
- Custom Emojis Parser: Auto-translates shortcodes (e.g. :smile: -> 😊) to Unicode
- In-App Alerts & Title-bar Flashing: Notifies user of new messages when unfocused, using winsound
- Aesthetic themes: Light/Dark selector matching AuraBMI, AuraPass, and AuraWeather
"""

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import sqlite3
import hashlib
import os
import json
import struct
import math
from datetime import datetime

# Windows systems sound support check
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Theme Palettes
THEMES = {
    "light": {
        "bg": "#f1f5f9",           # Slate 100
        "card_bg": "#ffffff",      # White
        "fg": "#0f172a",           # Slate 900
        "sub_fg": "#475569",       # Slate 600
        "accent": "#4f46e5",       # Indigo 600
        "accent_hover": "#4338ca", # Indigo 700
        "border": "#cbd5e1",       # Slate 300
    },
    "dark": {
        "bg": "#0f172a",           # Slate 900
        "card_bg": "#1e293b",      # Slate 800
        "fg": "#f8fafc",           # Slate 50
        "sub_fg": "#94a3b8",       # Slate 400
        "accent": "#6366f1",       # Indigo 400
        "accent_hover": "#4f46e5", # Indigo 500
        "border": "#334155",       # Slate 700
    }
}

# Common Emojis Translation Map
EMOJIS = {
    ":smile:": "😊",
    ":joy:": "😂",
    ":cry:": "😢",
    ":wink:": "😉",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":thumbsdown:": "👎",
    ":fire:": "🔥",
    ":laughing:": "😆",
    ":sunglasses:": "😎",
    ":thinking:": "🤔",
    ":clap:": "👏",
}


# =====================================================================
# SOCKET PACKET FRAMING HELPERS
# =====================================================================

def send_msg(sock, data):
    """Sends a length-prefixed JSON message over a socket."""
    try:
        serialized = json.dumps(data).encode('utf-8')
        # 4-byte length prefix in network byte order (big-endian)
        length_prefix = struct.pack('!I', len(serialized))
        sock.sendall(length_prefix + serialized)
        return True
    except socket.error:
        return False


def recv_msg(sock):
    """Receives a length-prefixed JSON message from a socket."""
    try:
        # Read the 4-byte length prefix
        raw_length = sock.recv(4)
        if not raw_length or len(raw_length) < 4:
            return None
        length = struct.unpack('!I', raw_length)[0]
        
        # Read the message body bytes in segments
        data = bytearray()
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data.extend(packet)
            
        return json.loads(data.decode('utf-8'))
    except (socket.error, json.JSONDecodeError):
        return None


# =====================================================================
# CRYPTO HELPERS
# =====================================================================

def hash_password(password, salt=None):
    """Hashes a password with pbkdf2_hmac using SHA256."""
    if salt is None:
        salt = os.urandom(16).hex()
    p_bytes = password.encode('utf-8')
    s_bytes = salt.encode('utf-8')
    h = hashlib.pbkdf2_hmac('sha256', p_bytes, s_bytes, 100000)
    return h.hex(), salt


# =====================================================================
# DUAL-MODE SERVER MONITOR CONSOLE
# =====================================================================

class ChatServerConsole:
    def __init__(self, root, host="127.0.0.1", port=5555):
        self.root = root
        self.host = host
        self.port = port
        
        self.root.title("AuraChat - Server Console")
        self.root.geometry("620x450")
        
        # Build layout
        self.create_widgets()
        
        # Active client list connection pools
        self.clients = {}         # username -> client socket connection
        self.client_rooms = {}    # client socket connection -> room string name
        
        # Database setup
        self.init_database()
        
        # Launch server socket listening thread
        self.server_sock = None
        self.is_running = True
        self.listen_thread = threading.Thread(target=self.start_socket_host, daemon=True)
        self.listen_thread.start()

    def create_widgets(self):
        """Builds logs monitor layout."""
        self.log_txt = tk.Text(self.root, bg="#0f172a", fg="#10b981", font=("Consolas", 10), state="disabled")
        self.log_txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        control_panel = tk.Frame(self.root)
        control_panel.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_lbl = tk.Label(control_panel, text="Server status: Booting...", font=("Segoe UI", 9, "bold"))
        self.status_lbl.pack(side=tk.LEFT)
        
        # Tag colors for logs
        self.log_txt.tag_config("info", foreground="#10b981")
        self.log_txt.tag_config("error", foreground="#ef4444")
        self.log_txt.tag_config("warn", foreground="#f59e0b")

    def log(self, text, tag="info"):
        """Inserts text timestamps into server window console."""
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.log_txt.configure(state="normal")
        self.log_txt.insert(tk.END, f"{timestamp}{text}\n", tag)
        self.log_txt.configure(state="disabled")
        self.log_txt.see(tk.END)

    def init_database(self):
        """Prepares sqlite storage schema."""
        try:
            self.db_conn = sqlite3.connect("chat_history.db", check_same_thread=False)
            self.cursor = self.db_conn.cursor()
            
            # Create user credentials
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL
                )
            ''')
            # Create message history log
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room TEXT NOT NULL,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.db_conn.commit()
            self.log("Database initialized successfully.")
        except sqlite3.Error as e:
            self.log(f"Database Initialization Failure: {e}", "error")

    def start_socket_host(self):
        """Starts socket server hosting loop on port config."""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reusing address
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen()
            
            self.status_lbl.configure(text=f"Hosting on {self.host}:{self.port}", fg="#10b981")
            self.log(f"Server is listening at TCP {self.host}:{self.port}...")
            
            while self.is_running:
                try:
                    c_sock, c_addr = self.server_sock.accept()
                    threading.Thread(target=self.client_connection_handler, args=(c_sock, c_addr), daemon=True).start()
                except socket.error:
                    break
        except Exception as e:
            self.log(f"Socket Bind Failure: {e}", "error")
            self.status_lbl.configure(text="Server Offline", fg="#ef4444")

    def client_connection_handler(self, sock, addr):
        """Manages separate incoming client message loops."""
        self.log(f"Incoming connection accepted from client address {addr[0]}:{addr[1]}.")
        username = None
        
        while self.is_running:
            req = recv_msg(sock)
            if not req:
                break
                
            req_type = req.get("type")
            
            # --- AUTH: REGISTER LOGIC ---
            if req_type == "register":
                uname = req.get("username", "").strip()
                pword = req.get("password", "")
                
                if not uname or not pword:
                    send_msg(sock, {"type": "auth_res", "success": False, "msg": "Blank inputs rejected."})
                    continue
                    
                p_hash, salt = hash_password(pword)
                try:
                    self.cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                                        (uname, p_hash, salt))
                    self.db_conn.commit()
                    self.log(f"Registered new profile: '{uname}'")
                    send_msg(sock, {"type": "auth_res", "success": True, "msg": "Registration successful! Proceed to Login."})
                except sqlite3.IntegrityError:
                    send_msg(sock, {"type": "auth_res", "success": False, "msg": "Username already exists."})
                except sqlite3.Error as e:
                    send_msg(sock, {"type": "auth_res", "success": False, "msg": f"Database error: {e}"})

            # --- AUTH: LOGIN LOGIC ---
            elif req_type == "login":
                uname = req.get("username", "").strip()
                pword = req.get("password", "")
                
                if uname in self.clients:
                    send_msg(sock, {"type": "auth_res", "success": False, "msg": "User is already logged in elsewhere."})
                    continue
                    
                try:
                    self.cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (uname,))
                    res = self.cursor.fetchone()
                    if res:
                        db_hash, db_salt = res
                        chk_hash, _ = hash_password(pword, db_salt)
                        if chk_hash == db_hash:
                            username = uname
                            self.clients[username] = sock
                            self.log(f"User '{username}' logged in successfully.")
                            send_msg(sock, {"type": "auth_res", "success": True, "msg": "Authenticated."})
                        else:
                            send_msg(sock, {"type": "auth_res", "success": False, "msg": "Invalid password credentials."})
                    else:
                        send_msg(sock, {"type": "auth_res", "success": False, "msg": "Username profile not found."})
                except sqlite3.Error as e:
                    send_msg(sock, {"type": "auth_res", "success": False, "msg": f"Database error: {e}"})

            # --- NAVIGATION: JOIN CHAT ROOM ---
            elif req_type == "join_room":
                if not username:
                    send_msg(sock, {"type": "join_res", "success": False, "msg": "Authentication token missing."})
                    continue
                    
                target_room = req.get("room", "").strip()
                if not target_room:
                    send_msg(sock, {"type": "join_res", "success": False, "msg": "Room name cannot be empty."})
                    continue

                # Leave prior room if active
                old_room = self.client_rooms.get(sock)
                if old_room:
                    self.broadcast_system_msg(old_room, f"{username} has left the room.")
                
                self.client_rooms[sock] = target_room
                self.log(f"User '{username}' joined room '{target_room}'")
                
                # Fetch history log for room
                history = []
                try:
                    self.cursor.execute('''
                        SELECT username, message, timestamp FROM messages 
                        WHERE room = ? 
                        ORDER BY timestamp ASC LIMIT 50
                    ''', (target_room,))
                    for row in self.cursor.fetchall():
                        h_user, h_msg, h_time = row
                        # Parse SQLite timestamp representation
                        dt = datetime.strptime(h_time, "%Y-%m-%d %H:%M:%S")
                        f_time = dt.strftime("%H:%M")
                        history.append({"username": h_user, "msg": h_msg, "time": f_time})
                except sqlite3.Error as e:
                    self.log(f"History query error: {e}", "warn")
                
                send_msg(sock, {"type": "join_res", "success": True, "room": target_room, "history": history})
                self.broadcast_system_msg(target_room, f"{username} has joined the room.")

            # --- MESSAGING: TRANSMIT MESSAGE ---
            elif req_type == "send_msg":
                if not username:
                    continue
                active_room = self.client_rooms.get(sock)
                if not active_room:
                    continue
                    
                msg_txt = req.get("msg", "").strip()
                if not msg_txt:
                    continue
                    
                # Save to database
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    self.cursor.execute("INSERT INTO messages (room, username, message, timestamp) VALUES (?, ?, ?, ?)",
                                        (active_room, username, msg_txt, timestamp_str))
                    self.db_conn.commit()
                except sqlite3.Error as e:
                    self.log(f"Failed to log message: {e}", "error")

                formatted_time = datetime.now().strftime("%H:%M")
                
                # Broadcast payload
                payload = {
                    "type": "broadcast_msg",
                    "username": username,
                    "msg": msg_txt,
                    "time": formatted_time
                }
                
                self.broadcast_to_room(active_room, payload)

        # Connection cleanup
        sock.close()
        if username and username in self.clients:
            del self.clients[username]
        if sock in self.client_rooms:
            exited_room = self.client_rooms[sock]
            del self.client_rooms[sock]
            if username:
                self.broadcast_system_msg(exited_room, f"{username} has disconnected.")
                self.log(f"User '{username}' disconnected.")
        else:
            self.log("Client socket connection closed.")

    def broadcast_to_room(self, room, payload):
        """Sends payload to all connections registered in the same room."""
        for client_sock, r_name in list(self.client_rooms.items()):
            if r_name == room:
                send_msg(client_sock, payload)

    def broadcast_system_msg(self, room, message):
        """Broadcasts server alerts (user joins/leaves)."""
        payload = {
            "type": "sys_msg",
            "msg": message
        }
        self.broadcast_to_room(room, payload)

    def shutdown(self):
        """Closes sockets and saves sqlite records."""
        self.is_running = False
        if self.server_sock:
            self.server_sock.close()
        for sock in list(self.clients.values()):
            sock.close()
        try:
            self.db_conn.close()
        except sqlite3.Error:
            pass


# =====================================================================
# DUAL-MODE CLIENT DASHBOARD
# =====================================================================

class ChatClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraChat Suite")
        self.root.geometry("900x580")
        self.root.minsize(800, 500)

        # Settings
        self.theme_var = tk.StringVar(value="light")
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.IntVar(value=5555)
        
        self.room_var = tk.StringVar()
        self.input_msg_var = tk.StringVar()
        
        # State variables
        self.sock = None
        self.is_connected = False
        self.current_user = None
        self.active_room = None
        self.joined_rooms_list = []
        
        # Notification alerts attributes
        self.original_title = self.root.title()
        self.is_flashing = False

        # Build Panels
        self.create_widgets()
        self.apply_theme()

        # Bind focus callback to clear notifications
        self.root.bind("<FocusIn>", self.on_window_focus_gained)

    def create_widgets(self):
        """Builds workspace frames."""
        # Main root wrapper
        self.main_wrapper = tk.Frame(self.root, bg="#f1f5f9", padx=15, pady=15)
        self.main_wrapper.pack(fill=tk.BOTH, expand=True)

        # ---------------------------------------------
        # 1. AUTHENTICATION PANEL (LOGIN / REGISTER SCREEN)
        # ---------------------------------------------
        self.auth_frame = tk.Frame(self.main_wrapper, bg="#ffffff", bd=1, relief="solid")
        self.auth_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=380, height=360)
        
        auth_inner = tk.Frame(self.auth_frame, bg="#ffffff", padx=25, pady=25)
        auth_inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(auth_inner, text="AURACHAT GATEWAY", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#4f46e5").pack(pady=(0, 10))

        # Fields
        tk.Label(auth_inner, text="Server IP Address:", bg="#ffffff").pack(anchor=tk.W, pady=1)
        self.host_ent = tk.Entry(auth_inner, textvariable=self.host_var, bg="#f8fafc", bd=0, highlightthickness=1)
        self.host_ent.pack(fill=tk.X, ipady=3, pady=(0, 5))

        tk.Label(auth_inner, text="Username:", bg="#ffffff").pack(anchor=tk.W, pady=1)
        self.uname_ent = tk.Entry(auth_inner, textvariable=self.username_var, bg="#f8fafc", bd=0, highlightthickness=1)
        self.uname_ent.pack(fill=tk.X, ipady=3, pady=(0, 5))

        tk.Label(auth_inner, text="Password:", bg="#ffffff").pack(anchor=tk.W, pady=1)
        self.pwd_ent = tk.Entry(auth_inner, textvariable=self.password_var, show="•", bg="#f8fafc", bd=0, highlightthickness=1)
        self.pwd_ent.pack(fill=tk.X, ipady=3, pady=(0, 15))

        # Action Buttons
        btn_f = tk.Frame(auth_inner, bg="#ffffff")
        btn_f.pack(fill=tk.X)
        btn_f.columnconfigure((0, 1), weight=1)

        self.login_btn = tk.Button(btn_f, text="Login", bg="#4f46e5", fg="white", font=("Segoe UI", 9, "bold"),
                                   relief="flat", bd=0, command=self.perform_login_action)
        self.login_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=5)

        self.reg_btn = tk.Button(btn_f, text="Register", bg="#e2e8f0", fg="#0f172a", font=("Segoe UI", 9),
                                 relief="flat", bd=0, command=self.perform_registration_action)
        self.reg_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=5)

        # ---------------------------------------------
        # 2. CHAT PANEL (DASHBOARD SCREEN - HIDDEN BY DEFAULT)
        # ---------------------------------------------
        self.chat_frame = tk.Frame(self.main_wrapper, bg="#f1f5f9")
        # Gridded/packed conditionally on successful login
        
        # Configure columns (Left sidebar has 260px width, chat workspace occupies the rest)
        self.chat_frame.columnconfigure(0, weight=0, minsize=260)
        self.chat_frame.columnconfigure(1, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)

        # -- SIDEBAR PANELS (Left Column) --
        sidebar = tk.Frame(self.chat_frame, bg="#ffffff", bd=1, relief="solid")
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        sidebar_inner = tk.Frame(sidebar, bg="#ffffff", padx=12, pady=12)
        sidebar_inner.pack(fill=tk.BOTH, expand=True)

        self.profile_lbl = tk.Label(sidebar_inner, text="Profile: Username", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a", anchor=tk.W)
        self.profile_lbl.pack(fill=tk.X, pady=(0, 10))

        # Room management
        tk.Label(sidebar_inner, text="CREATE / JOIN ROOM:", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#64748b").pack(anchor=tk.W, pady=(5, 3))
        
        room_row = tk.Frame(sidebar_inner, bg="#ffffff")
        room_row.pack(fill=tk.X, pady=(0, 10))
        
        self.room_ent = tk.Entry(room_row, textvariable=self.room_var, bg="#f8fafc", bd=0, highlightthickness=1)
        self.room_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 4))
        self.room_ent.bind("<Return>", lambda e: self.join_room_action())
        
        self.join_btn = tk.Button(room_row, text="Join", bg="#4f46e5", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=8, command=self.join_room_action)
        self.join_btn.pack(side=tk.RIGHT, ipady=3)

        # Rooms Listbox
        tk.Label(sidebar_inner, text="CHANNELS:", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#64748b").pack(anchor=tk.W, pady=(5, 3))
        
        self.rooms_box = tk.Listbox(sidebar_inner, bg="#f8fafc", selectbackground="#4f46e5", selectforeground="white", font=("Segoe UI", 9), relief=tk.FLAT, bd=1, highlightbackground="#cbd5e1")
        self.rooms_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.rooms_box.bind("<<ListboxSelect>>", self.on_room_listbox_select)

        # Theme selectors
        theme_f = tk.Frame(sidebar_inner, bg="#ffffff")
        theme_f.pack(fill=tk.X)
        
        theme_btn_light = ttk.Radiobutton(theme_f, text="☀️ Light", variable=self.theme_var, value="light", command=self.apply_theme)
        theme_btn_light.pack(side=tk.LEFT, expand=True)
        theme_btn_dark = ttk.Radiobutton(theme_f, text="🌙 Dark", variable=self.theme_var, value="dark", command=self.apply_theme)
        theme_btn_dark.pack(side=tk.LEFT, expand=True)

        # -- CONVERSATION ROOMS (Right Column) --
        chat_pane = tk.Frame(self.right_col_pane_config() if False else self.chat_frame, bg="#ffffff", bd=1, relief="solid")
        chat_pane.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        chat_pane_inner = tk.Frame(chat_pane, bg="#ffffff", padx=15, pady=15)
        chat_pane_inner.pack(fill=tk.BOTH, expand=True)

        # Room header
        self.room_header_lbl = tk.Label(chat_pane_inner, text="Select or Join a Room", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#4f46e5")
        self.room_header_lbl.pack(anchor=tk.W, pady=(0, 10))

        # Main scrollable Text Area for chat histories
        self.chat_txt = tk.Text(chat_pane_inner, font=("Segoe UI", 10), state="disabled", wrap=tk.WORD, relief=tk.FLAT, bg="#f8fafc")
        self.chat_txt.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Tags styling inside chat_txt logs
        self.chat_txt.tag_config("mine_lbl", justify=tk.RIGHT, foreground="#4f46e5", font=("Segoe UI", 9, "bold"))
        self.chat_txt.tag_config("mine_val", justify=tk.RIGHT, foreground="#0f172a", font=("Segoe UI", 10))
        self.chat_txt.tag_config("other_lbl", justify=tk.LEFT, foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.chat_txt.tag_config("other_val", justify=tk.LEFT, foreground="#0f172a", font=("Segoe UI", 10))
        self.chat_txt.tag_config("sys", justify=tk.CENTER, foreground="#94a3b8", font=("Segoe UI", 9, "italic"))

        # Message Entry Row
        entry_row = tk.Frame(chat_pane_inner, bg="#ffffff")
        entry_row.pack(fill=tk.X)

        self.msg_entry = tk.Entry(entry_row, textvariable=self.input_msg_var, font=("Segoe UI", 11),
                                  bg="#f8fafc", bd=0, highlightthickness=1, highlightbackground="#cbd5e1",
                                  highlightcolor="#4f46e5")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 5))
        self.msg_entry.bind("<Return>", lambda e: self.send_message_action())

        # Emoji Shortcut Dropdown list
        self.emoji_btn = tk.Button(entry_row, text="😃 Emojis", bg="#e2e8f0", fg="#0f172a", font=("Segoe UI", 9),
                                   relief="flat", bd=0, padx=10, command=self.open_emoji_selector)
        self.emoji_btn.pack(side=tk.LEFT, padx=3, ipady=4)

        self.send_btn = tk.Button(entry_row, text="Send", bg="#4f46e5", fg="white", font=("Segoe UI", 9, "bold"),
                                  relief="flat", bd=0, padx=15, command=self.send_message_action)
        self.send_btn.pack(side=tk.RIGHT, ipady=4)

    def connect_to_server(self):
        """Attempts connection, launches receiver loop thread."""
        if self.is_connected:
            return True
            
        host = self.host_var.get().strip()
        port = self.port_var.get()
        
        if not host:
            messagebox.showerror("Error", "Server address IP required.")
            return False
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
            
            # Start background message listener
            threading.Thread(target=self.receive_messages_loop, daemon=True).start()
            return True
        except socket.error as e:
            messagebox.showerror("Connection Refused", f"Could not connect to AuraChat Server:\n{e}")
            self.is_connected = False
            return False

    def perform_registration_action(self):
        """Sends registration credentials request."""
        if not self.connect_to_server():
            return
            
        uname = self.username_var.get().strip()
        pword = self.password_var.get()
        
        if not uname or not pword:
            messagebox.showwarning("Validation Warning", "Username and Password fields cannot be empty.")
            return
            
        payload = {"type": "register", "username": uname, "password": pword}
        send_msg(self.sock, payload)

    def perform_login_action(self):
        """Sends authentication request."""
        if not self.connect_to_server():
            return
            
        uname = self.username_var.get().strip()
        pword = self.password_var.get()
        
        if not uname or not pword:
            messagebox.showwarning("Validation Warning", "Username and Password fields cannot be empty.")
            return
            
        payload = {"type": "login", "username": uname, "password": pword}
        send_msg(self.sock, payload)

    def join_room_action(self):
        """Requests room entry change."""
        room_name = self.room_var.get().strip()
        if not room_name:
            return
        
        # Room naming conventions sanitize (prefix hash if not already there)
        if not room_name.startswith("#"):
            room_name = f"#{room_name}"
            
        payload = {"type": "join_room", "room": room_name}
        send_msg(self.sock, payload)
        self.room_var.set("") # Clear input

    def on_room_listbox_select(self, event=None):
        """Handles listbox switching joined channels."""
        selection = self.rooms_box.curselection()
        if selection:
            selected_room = self.rooms_box.get(selection[0])
            if selected_room != self.active_room:
                payload = {"type": "join_room", "room": selected_room}
                send_msg(self.sock, payload)

    def send_message_action(self):
        """Dispatches active message entry, parsing emoji shortcodes."""
        text = self.input_msg_var.get().strip()
        if not text or not self.active_room:
            return
            
        # Emoji shortcode parsing
        text = self.translate_emojis(text)
        
        payload = {"type": "send_msg", "msg": text}
        send_msg(self.sock, payload)
        self.input_msg_var.set("") # Reset entry box

    def translate_emojis(self, text):
        """Replaces codes with actual unicode characters."""
        for code, emoji in EMOJIS.items():
            text = text.replace(code, emoji)
        return text

    def open_emoji_selector(self):
        """Builds a floating window context listing shortcodes."""
        emoji_win = tk.Toplevel(self.root)
        emoji_win.title("Emoji Drawer")
        emoji_win.geometry("260x220")
        emoji_win.resizable(False, False)
        emoji_win.transient(self.root)
        emoji_win.grab_set()

        # Center relative to cursor
        emoji_win.geometry(f"+{self.root.winfo_pointerx()}+{self.root.winfo_pointery()}")

        theme = THEMES[self.theme_var.get()]
        emoji_win.configure(bg=theme["bg"])

        tk.Label(emoji_win, text="Click to insert:", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9, "bold")).pack(pady=8)

        grid_frame = tk.Frame(emoji_win, bg=theme["bg"])
        grid_frame.pack(padx=10, pady=5)

        # Render grid of emojis
        for idx, (code, emoji) in enumerate(EMOJIS.items()):
            r = idx // 4
            c = idx % 4
            btn = tk.Button(grid_frame, text=emoji, font=("Segoe UI", 12), width=3, bg=theme["card_bg"], fg=theme["fg"],
                            relief="flat", bd=0, command=lambda e_code=code: insert_emoji(e_code))
            btn.grid(row=r, column=c, padx=3, pady=3)

        def insert_emoji(e_code):
            current_text = self.input_msg_var.get()
            self.input_msg_var.set(f"{current_text} {e_code} ")
            self.msg_entry.focus()
            emoji_win.destroy()

    def receive_messages_loop(self):
        """Message loop receiver thread."""
        while self.is_connected:
            msg = recv_msg(self.sock)
            if not msg:
                break
                
            msg_type = msg.get("type")
            
            # --- AUTH RESPONSE ---
            if msg_type == "auth_res":
                success = msg.get("success", False)
                reason = msg.get("msg", "")
                if success:
                    self.current_user = self.username_var.get().strip()
                    self.root.after(0, self.transition_to_dashboard)
                else:
                    self.root.after(0, lambda r=reason: messagebox.showerror("Auth Error", r))
                    
            # --- JOIN RESPONSE ---
            elif msg_type == "join_res":
                success = msg.get("success", False)
                if success:
                    r_name = msg.get("room")
                    self.active_room = r_name
                    history = msg.get("history", [])
                    self.root.after(0, lambda r=r_name, h=history: self.load_room_session(r, h))
                else:
                    reason = msg.get("msg", "")
                    self.root.after(0, lambda r=reason: messagebox.showerror("Join Error", r))

            # --- BROADCASTED MESSAGE ARRIVED ---
            elif msg_type == "broadcast_msg":
                sender = msg.get("username")
                msg_txt = msg.get("msg")
                time_str = msg.get("time")
                self.root.after(0, lambda s=sender, m=msg_txt, t=time_str: self.append_message(s, m, t))

            # --- BROADCASTED SYSTEM MESSAGE ARRIVED ---
            elif msg_type == "sys_msg":
                msg_txt = msg.get("msg")
                self.root.after(0, lambda m=msg_txt: self.append_system_message(m))

        self.is_connected = False
        self.root.after(0, self.on_connection_lost)

    def transition_to_dashboard(self):
        """Hides login frames, shows chat panels."""
        self.auth_frame.place_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.profile_lbl.configure(text=f"Profile: {self.current_user}")
        self.original_title = f"AuraChat - {self.current_user}"
        self.root.title(self.original_title)
        
        # Default join global lobby
        payload = {"type": "join_room", "room": "#lobby"}
        send_msg(self.sock, payload)

    def load_room_session(self, room_name, history):
        """Sets active room text area, populates historical SQLite logs."""
        self.room_header_lbl.configure(text=f"Active Room: {room_name}")
        
        # Add to channels list if not already logged
        if room_name not in self.joined_rooms_list:
            self.joined_rooms_list.append(room_name)
            self.rooms_box.insert(tk.END, room_name)
            
        # Select active channel listbox index
        idx = self.joined_rooms_list.index(room_name)
        self.rooms_box.selection_clear(0, tk.END)
        self.rooms_box.selection_set(idx)

        # Clear text log
        self.chat_txt.configure(state="normal")
        self.chat_txt.delete("1.0", tk.END)
        self.chat_txt.configure(state="disabled")
        
        # Inject history
        for record in history:
            self.append_message(record["username"], record["msg"], record["time"], run_alert=False)

    def append_message(self, sender, text, timestamp, run_alert=True):
        """Inserts chat bubbles into text area."""
        self.chat_txt.configure(state="normal")
        
        if sender == self.current_user:
            # Self messages (Right aligned)
            self.chat_txt.insert(tk.END, f"\n[{timestamp}] You\n", "mine_lbl")
            self.chat_txt.insert(tk.END, f"{text}\n", "mine_val")
        else:
            # Other users (Left aligned)
            self.chat_txt.insert(tk.END, f"\n[{timestamp}] {sender}\n", "other_lbl")
            self.chat_txt.insert(tk.END, f"{text}\n", "other_val")
            
            # Notification alerts
            if run_alert:
                self.trigger_unfocused_notification()
                
        self.chat_txt.configure(state="disabled")
        self.chat_txt.see(tk.END)

    def append_system_message(self, text):
        """Inserts italicized alerts in center columns."""
        self.chat_txt.configure(state="normal")
        self.chat_txt.insert(tk.END, f"\n[System] {text}\n", "sys")
        self.chat_txt.configure(state="disabled")
        self.chat_txt.see(tk.END)

    def trigger_unfocused_notification(self):
        """Title flashes and asterisk chime rings if windows is not selected."""
        # Check window focus state
        if self.root.focus_get() is None:
            # Flashing
            if not self.is_flashing:
                self.is_flashing = True
                self.flash_title_loop()
                
            # Sound chime
            if HAS_WINSOUND:
                try:
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception:
                    pass

    def flash_title_loop(self):
        """Animates window frames header title."""
        if not self.is_flashing:
            self.root.title(self.original_title)
            return
            
        current = self.root.title()
        if current.startswith("💬 * NEW MSG *"):
            self.root.title(self.original_title)
        else:
            self.root.title(f"💬 * NEW MSG * {self.original_title}")
            
        self.root.after(800, self.flash_title_loop)

    def on_window_focus_gained(self, event=None):
        """Clears flashing loop when window is active."""
        self.is_flashing = False
        self.root.title(self.original_title)

    def on_connection_lost(self):
        """Gracefully alerts user, transitions to login."""
        self.chat_frame.pack_forget()
        self.auth_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=380, height=360)
        self.rooms_box.delete(0, tk.END)
        self.joined_rooms_list.clear()
        self.active_room = None
        self.current_user = None
        messagebox.showwarning("Disconnect Warning", "Lost connection to the AuraChat Server.")

    def apply_theme(self):
        """Styles widget sets dynamically."""
        theme = THEMES[self.theme_var.get()]
        self.root.configure(bg=theme["bg"])
        self.main_wrapper.configure(bg=theme["bg"])

        # Styled ttk Radio Buttons
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure("TRadiobutton", background=theme["card_bg"] if self.chat_frame.winfo_ismapped() else theme["bg"], foreground=theme["fg"])

        # Walk panels
        self.recursive_theme_update(self.root, theme)

    def recursive_theme_update(self, widget, theme):
        """Walks hierarchy applying tags mapping overlays."""
        w_class = widget.winfo_class()
        
        try:
            if widget in [self.auth_frame, self.rooms_box, self.chat_txt]:
                widget.configure(bg=theme["card_bg"], highlightbackground=theme["border"])
            elif w_class == "Frame":
                parent_style = widget.master.winfo_class()
                # Use card background for cards layout containers
                if widget.master == self.auth_frame or widget.master == self.chat_frame:
                    widget.configure(bg=theme["card_bg"])
                else:
                    widget.configure(bg=theme["bg"])
            elif w_class == "Label":
                # Detect container context
                if widget.master == self.auth_frame or widget.master.master == self.auth_frame:
                    widget.configure(bg=theme["card_bg"], fg=theme["fg"])
                elif widget.master.master == self.chat_frame or widget.master.master.master == self.chat_frame:
                    widget.configure(bg=theme["card_bg"], fg=theme["fg"])
                else:
                    widget.configure(bg=theme["bg"], fg=theme["fg"])
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=theme["bg"] if widget == self.msg_entry else theme["card_bg"],
                                 fg=theme["fg"], insertbackground=theme["fg"],
                                 highlightbackground=theme["border"], highlightcolor=theme["accent"])
            elif isinstance(widget, tk.Button):
                # Standard Tk buttons on cards configurations
                if widget in [self.login_btn, self.join_btn, self.send_btn]:
                    widget.configure(bg=theme["accent"], fg="white", activebackground=theme["accent_hover"], activeforeground="white")
                else:
                    widget.configure(bg=theme["border"], fg=theme["fg"], activebackground=theme["bg"], activeforeground=theme["fg"])
        except Exception:
            pass
            
        for child in widget.winfo_children():
            self.recursive_theme_update(child, theme)

    def close_connection(self):
        """Close socket connection gracefully."""
        self.is_connected = False
        if self.sock:
            try:
                self.sock.close()
            except socket.error:
                pass
        self.root.destroy()


# =====================================================================
# MULTI-MODE DIALOG SELECTOR LAUNCHER
# =====================================================================

class DualModeLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraChat Launcher")
        self.root.geometry("380x180")
        self.root.resizable(False, False)
        
        # Visual setup
        main_f = tk.Frame(self.root, bg="#f1f5f9", padx=20, pady=20)
        main_f.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_f, text="AuraChat Startup Options", font=("Segoe UI", 12, "bold"), bg="#f1f5f9", fg="#4f46e5").pack(pady=(0, 15))
        
        btn_row = tk.Frame(main_f, bg="#f1f5f9")
        btn_row.pack(fill=tk.X)
        btn_row.columnconfigure((0, 1), weight=1)
        
        server_btn = tk.Button(btn_row, text="🖥️ Launch Chat Server", font=("Segoe UI", 10, "bold"), bg="#10b981", fg="white",
                               activebackground="#059669", activeforeground="white", relief="flat", bd=0, padx=10, pady=10,
                               command=self.launch_server_console)
        server_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        client_btn = tk.Button(btn_row, text="💬 Launch Chat Client", font=("Segoe UI", 10, "bold"), bg="#4f46e5", fg="white",
                               activebackground="#4338ca", activeforeground="white", relief="flat", bd=0, padx=10, pady=10,
                               command=self.launch_client_app)
        client_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        tk.Label(main_f, text="Port default: 5555 | SQLite persistence active", font=("Segoe UI", 8), bg="#f1f5f9", fg="#64748b").pack(pady=(15, 0))

    def launch_server_console(self):
        """Switches execution to Server window."""
        self.root.destroy()
        new_root = tk.Tk()
        app = ChatServerConsole(new_root)
        
        def on_close():
            app.shutdown()
            new_root.destroy()
            
        new_root.protocol("WM_DELETE_WINDOW", on_close)
        new_root.mainloop()

    def launch_client_app(self):
        """Switches execution to Client window."""
        self.root.destroy()
        new_root = tk.Tk()
        app = ChatClientApp(new_root)
        
        new_root.protocol("WM_DELETE_WINDOW", app.close_connection)
        new_root.mainloop()


# =====================================================================
# MAIN ENTRY POINT
# =====================================================================

def main():
    root = tk.Tk()
    app = DualModeLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
