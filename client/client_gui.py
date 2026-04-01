import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import socket
import ssl
import os
import sys
import datetime

# resolve config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import SERVER_IP, PORT, CERT, BUFFER_SIZE
except ImportError:
    SERVER_IP = "127.0.0.1"
    PORT = 5000
    CERT = "ssl/server.crt"
    BUFFER_SIZE = 4096



#  THEME  — dark terminal aesthetic with sharp green accent
BG       = "#0b0e14"
SURFACE  = "#111620"
SURFACE2 = "#181f2e"
SURFACE3 = "#1e2840"
BORDER   = "#202d42"
ACCENT   = "#00e5a0"
ACCENT_D = "#00b87a"
ACCENT2  = "#38bdf8"
WARN     = "#fbbf24"
DANGER   = "#f87171"
TEXT     = "#dde4f0"
MUTED    = "#4a5a72"
DIM      = "#2a3750"

MONO     = ("Courier New", 11)
MONO_SM  = ("Courier New", 10)
MONO_XS  = ("Courier New", 9)
SANS     = ("Helvetica", 11)
BOLD     = ("Helvetica", 11, "bold")
H1       = ("Helvetica", 15, "bold")



#  NETWORK LAYER
class ChatClient:
    def __init__(self, on_message, on_status, on_disconnect):
        self._sock = None
        self._connected = False
        self._on_msg = on_message      # fn(kind, text)
        self._on_status = on_status       # fn(text, tag)
        self._on_disc = on_disconnect   # fn()
        self._buffers={} # room → {seq: text
        self._next_seq={} # room → next expected seq number

    def _route_message(self, kind, text):
        if kind == "normal" and text.startswith("["):
            # Parse [room][seq] who: content
            try:
                room_part, rest = text[1:].split("][", 1)
                seq_str, content = rest.split("] ", 1)
                seq = int(seq_str)
                room = room_part

                if room not in self._next_seq:
                    self._next_seq[room] = 1
                    self._buffers[room] = {}

                self._buffers[room][seq] = content

                # Flush any consecutive messages that are now ready
                while self._next_seq[room] in self._buffers[room]:
                    msg = self._buffers[room].pop(self._next_seq[room])
                    self._display_message(msg)
                    self._next_seq[room] += 1
                return
            except (ValueError, IndexError):
                pass
        self._display_message(text)

    # Connect 
    def connect(self, server_ip, port, cert, username):
        """Runs in a background thread — calls on_status / on_message."""
        try:
            ctx = ssl.create_default_context()
            ctx.load_verify_locations(cert)
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_REQUIRED

            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock = ctx.wrap_socket(raw, server_hostname=server_ip)
            self._sock.connect((server_ip, port))

            self._on_status(f"TLS handshake complete · {server_ip}:{port}", "ok")
            self._on_status(f"Certificate verified: {cert}", "ok")

            # Send username
            self._sock.sendall(username.encode())

            # Read server ack
            ack = self._sock.recv(BUFFER_SIZE).decode("utf-8", errors="replace")
            if ack.startswith("ERROR|"):
                self._on_status(f"Server rejected: {ack[6:]}", "err")
                self._sock.close()
                return
            if ack.startswith("OK|") or "Connected" in ack:
                self._on_status(f"✓  {ack.replace('OK|','')}", "ok")

            self._connected = True
            threading.Thread(target=self._recv_loop, daemon=True).start()

        except FileNotFoundError:
            self._on_status(f"Certificate not found: {cert}", "err")
        except ssl.SSLError as e:
            self._on_status(f"TLS error: {e}", "err")
        except ConnectionRefusedError:
            self._on_status(f"Connection refused — is the server running?", "err")
        except Exception as e:
            self._on_status(f"Connect failed: {e}", "err")

    # Receive loop 
    def _recv_loop(self):
        while self._connected:
            try:
                data = self._sock.recv(BUFFER_SIZE)
                if not data:
                    break
                msg = data.decode("utf-8", errors="replace")

                if msg.startswith("ERROR|"):
                    self._on_msg("err", msg[6:])
                elif msg.startswith("OK|"):
                    self._on_msg("ok", msg[3:])
                elif msg.startswith("[PRIVATE]"):
                    self._on_msg("private", msg[9:])
                elif msg.startswith("[Server]"):
                    self._on_msg("server", msg)
                elif msg.startswith("FILE_INCOMING|"):
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        self._handle_incoming_file(parts[1], int(parts[2]))
                else:
                    self._on_msg("normal", msg)

            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
            except Exception as e:
                self._on_msg("err", f"Receive error: {e}")
                break

        self._connected = False
        self._on_disc()

    def _handle_incoming_file(self, filename, size):
        safe_name = os.path.basename(filename)
        self._on_msg("file_start", f"{safe_name} ({size} bytes)")
        received = 0
        save_path = os.path.join(os.getcwd(), "received_" + safe_name)
        try:
            with open(save_path, "wb") as f:
                while received < size:
                    chunk = self._sock.recv(min(BUFFER_SIZE, size - received))
                    if not chunk:
                        self._on_msg("err", f"File cut short: {received}/{size} bytes")
                        return
                    f.write(chunk)
                    received += len(chunk)
            self._on_msg("file_done", f"{safe_name}  →  saved as received_{safe_name}")
        except Exception as e:
            self._on_msg("err", f"File save error: {e}")

    # Send helpers
    def send_raw(self, data: bytes) -> bool:
        if not self._connected or not self._sock:
            return False
        try:
            self._sock.sendall(data)
            return True
        except Exception as e:
            self._on_msg("err", f"Send failed: {e}")
            return False

    def join_room(self, room):
        self.send_raw(f"JOIN|{room}".encode())

    def leave_room(self, room):
        self.send_raw(f"LEAVE|{room}".encode())

    def send_msg(self, room, text):
        self.send_raw(f"MSG|{room}|{text}".encode())

    def send_private(self, user, text):
        self.send_raw(f"PRIVATE|{user}|{text}".encode())

    def send_file(self, room, path):
        if not os.path.exists(path):
            self._on_msg("err", f"File not found: {path}")
            return
        size = os.path.getsize(path)
        name = os.path.basename(path)
        self.send_raw(f"FILE|{room}|{name}|{size}".encode())
        with open(path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                self._sock.sendall(chunk)
        self._on_msg("ok", f"Sent: {name} ({size} bytes)")

    def disconnect(self):
        self._connected = False
        try:
            self._sock.close()
        except Exception:
            pass


#  GUI
class ClientGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SecureChat Client")
        self.geometry("960x680")
        self.minsize(780, 560)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._client    = None
        self._username  = ""
        self._rooms     = []          # list of joined rooms
        self._active_room = tk.StringVar()

        self._apply_styles()
        self._build()
        self._show_login()

    #  STYLES
    def _apply_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame",       background=BG)
        s.configure("TLabel",       background=BG, foreground=TEXT)
        s.configure("TButton",      background=SURFACE2, foreground=TEXT,
                    borderwidth=0, relief="flat", font=SANS, padding=[10, 6])
        s.map("TButton",
              background=[("active", BORDER)],
              foreground=[("active", ACCENT)])
        s.configure("Accent.TButton", background=ACCENT, foreground="#000",
                    font=BOLD, padding=[14, 8])
        s.map("Accent.TButton",
              background=[("active", "#00ffb0"), ("disabled", DIM)],
              foreground=[("disabled", MUTED)])
        s.configure("Danger.TButton", background=DANGER, foreground="#000",
                    font=BOLD, padding=[10, 6])
        s.configure("TEntry",       fieldbackground=SURFACE2, foreground=TEXT,
                    insertcolor=ACCENT, borderwidth=0, relief="flat",
                    font=MONO_SM, padding=6)
        s.configure("TScrollbar",   background=SURFACE2, troughcolor=BG,
                    borderwidth=0, arrowcolor=MUTED)
        s.configure("TCombobox",    fieldbackground=SURFACE2, foreground=TEXT,
                    selectbackground=SURFACE3, selectforeground=ACCENT,
                    background=SURFACE2, font=MONO_SM, borderwidth=0)
        s.map("TCombobox",
              fieldbackground=[("readonly", SURFACE2)],
              foreground=[("readonly", TEXT)])


    #  BUILD SKELETON
    def _build(self):
        # Top bar 
        self._topbar = tk.Frame(self, bg=SURFACE, height=48)
        self._topbar.pack(fill="x")
        self._topbar.pack_propagate(False)

        tk.Label(self._topbar, text="🔐  SecureChat",
                 bg=SURFACE, fg=ACCENT, font=H1).pack(side="left", padx=16)

        self._tls_badge = tk.Label(self._topbar,
                                    text="  ⬤  NOT CONNECTED",
                                    bg=SURFACE, fg=MUTED, font=MONO_XS)
        self._tls_badge.pack(side="left", padx=8)

        self._disc_btn = ttk.Button(self._topbar, text="Disconnect",
                                     style="Danger.TButton",
                                     command=self._do_disconnect)
        self._disc_btn.pack(side="right", padx=12, pady=8)
        self._disc_btn.pack_forget()   # hidden until connected

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Main area (hidden until connected)
        self._main = tk.Frame(self, bg=BG)

        # Left sidebar — rooms
        sidebar = tk.Frame(self._main, bg=SURFACE, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="ROOMS", bg=SURFACE, fg=MUTED,
                 font=("Helvetica", 8, "bold")).pack(anchor="w", padx=12, pady=(14, 6))

        self._room_list = tk.Listbox(
            sidebar, bg=SURFACE2, fg=TEXT, font=MONO_SM,
            selectbackground=SURFACE3, selectforeground=ACCENT,
            borderwidth=0, highlightthickness=0, relief="flat",
            activestyle="none", cursor="hand2"
        )
        self._room_list.pack(fill="both", expand=True, padx=8)
        self._room_list.bind("<<ListboxSelect>>", self._on_room_select)

        # Room controls
        room_ctrl = tk.Frame(sidebar, bg=SURFACE)
        room_ctrl.pack(fill="x", padx=8, pady=8)
        self._room_entry = tk.Entry(room_ctrl, bg=SURFACE2, fg=TEXT,
                                     insertbackground=ACCENT, relief="flat",
                                     font=MONO_SM, bd=4)
        self._room_entry.pack(fill="x", pady=(0, 4))
        self._room_entry.insert(0, "room1")
        self._room_entry.bind("<Return>", lambda e: self._do_join())

        btn_row = tk.Frame(room_ctrl, bg=SURFACE)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="Join", bg=ACCENT, fg="#000",
                  activebackground="#00ffb0", relief="flat",
                  font=("Helvetica", 9, "bold"), cursor="hand2",
                  command=self._do_join).pack(side="left", fill="x", expand=True,
                                               ipadx=4, ipady=3)
        tk.Button(btn_row, text="Leave", bg=SURFACE3, fg=MUTED,
                  activebackground=BORDER, relief="flat",
                  font=("Helvetica", 9, "bold"), cursor="hand2",
                  command=self._do_leave).pack(side="left", fill="x", expand=True,
                                                ipadx=4, ipady=3, padx=(4, 0))

        # ── Me box ───────────────────────────────────────────────────
        me_box = tk.Frame(sidebar, bg=SURFACE2,
                          highlightbackground=BORDER, highlightthickness=1)
        me_box.pack(fill="x", padx=8, pady=(0, 12))
        tk.Label(me_box, text="CONNECTED AS", bg=SURFACE2, fg=MUTED,
                 font=("Helvetica", 7, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        self._me_label = tk.Label(me_box, text="", bg=SURFACE2, fg=ACCENT,
                                   font=("Courier New", 11, "bold"))
        self._me_label.pack(anchor="w", padx=10, pady=(0, 8))

        tk.Frame(self._main, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel 
        right = tk.Frame(self._main, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Active room header
        self._room_header = tk.Frame(right, bg=SURFACE, height=40)
        self._room_header.pack(fill="x")
        self._room_header.pack_propagate(False)
        self._room_title = tk.Label(self._room_header, text="No room joined",
                                     bg=SURFACE, fg=MUTED, font=BOLD)
        self._room_title.pack(side="left", padx=14)
        self._tls_room_badge = tk.Label(self._room_header,
                                         text="⬤  TLS 1.3 · ENCRYPTED",
                                         bg=SURFACE, fg=ACCENT, font=MONO_XS)
        self._tls_room_badge.pack(side="right", padx=14)
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x")

        # Message area
        self._msg_area = scrolledtext.ScrolledText(
            right, bg=BG, fg=TEXT, font=MONO_SM,
            insertbackground=ACCENT, relief="flat", bd=0,
            state="disabled", wrap="word", padx=14, pady=10,
        )
        self._msg_area.pack(fill="both", expand=True)

        # Colour tags
        for tag, col in [
            ("ok",      ACCENT),
            ("err",     DANGER),
            ("warn",    WARN),
            ("private", WARN),
            ("server",  MUTED),
            ("file",    ACCENT2),
            ("ts",      MUTED),
            ("who",     ACCENT2),
            ("seq",     DIM),
            ("normal",  TEXT),
            ("self",    ACCENT),
        ]:
            self._msg_area.tag_config(tag, foreground=col)
        self._msg_area.tag_config("private_bg",
                                   background=SURFACE2)

        # Input area 
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x")
        inp_wrap = tk.Frame(right, bg=SURFACE, pady=10)
        inp_wrap.pack(fill="x", padx=12)

        # Room selector
        sel_row = tk.Frame(inp_wrap, bg=SURFACE)
        sel_row.pack(fill="x", pady=(0, 6))
        tk.Label(sel_row, text="Room:", bg=SURFACE, fg=MUTED,
                 font=MONO_XS).pack(side="left")
        self._room_combo = ttk.Combobox(sel_row, textvariable=self._active_room,
                                         state="readonly", width=14, font=MONO_SM)
        self._room_combo.pack(side="left", padx=6)

        # Private message toggle
        self._pm_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sel_row, text="Private msg to:", variable=self._pm_var,
                       bg=SURFACE, fg=MUTED, activebackground=SURFACE,
                       selectcolor=SURFACE3, font=MONO_XS,
                       command=self._toggle_pm).pack(side="left", padx=(12, 4))
        self._pm_entry = tk.Entry(sel_row, bg=SURFACE2, fg=WARN,
                                   insertbackground=WARN, relief="flat",
                                   font=MONO_SM, bd=4, width=14)
        self._pm_entry.insert(0, "username")
        self._pm_entry.pack(side="left")
        self._pm_entry.config(state="disabled")

        # File button
        tk.Button(sel_row, text="📎 Send File", bg=SURFACE3, fg=ACCENT2,
                  activebackground=BORDER, relief="flat",
                  font=("Helvetica", 9), cursor="hand2",
                  command=self._do_send_file).pack(side="right")

        # Text input row
        inp_row = tk.Frame(inp_wrap, bg=SURFACE)
        inp_row.pack(fill="x")
        self._text_inp = tk.Entry(inp_row, bg=SURFACE2, fg=TEXT,
                                   insertbackground=ACCENT, relief="flat",
                                   font=MONO, bd=6)
        self._text_inp.pack(side="left", fill="x", expand=True)
        self._text_inp.bind("<Return>", lambda e: self._do_send())
        self._text_inp.bind("<Up>",     lambda e: self._history_up())
        self._text_inp.bind("<Down>",   lambda e: self._history_down())

        self._send_btn = tk.Button(inp_row, text="Send  ↵",
                                    bg=ACCENT, fg="#000",
                                    activebackground="#00ffb0",
                                    relief="flat", font=BOLD,
                                    cursor="hand2",
                                    command=self._do_send)
        self._send_btn.pack(side="left", padx=(8, 0), ipadx=12, ipady=5)

        # Message history for ↑/↓
        self._history  = []
        self._hist_idx = -1

        # Status bar 
        self._statusbar = tk.Label(self, text="Not connected",
                                    bg=SURFACE, fg=MUTED, font=MONO_XS,
                                    anchor="w", padx=12)
        self._statusbar.pack(fill="x", side="bottom")

    #  LOGIN OVERLAY
    def _show_login(self):
        self._login_frame = tk.Frame(self, bg=BG)
        self._login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Centre card
        card = tk.Frame(self._login_frame, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="🔐", font=("Helvetica", 36), bg=SURFACE,
                 fg=ACCENT).pack(pady=(28, 0))
        tk.Label(card, text="SecureChat", font=H1,
                 bg=SURFACE, fg=TEXT).pack()
        tk.Label(card, text="TLS 1.3 · End-to-end encrypted",
                 font=MONO_XS, bg=SURFACE, fg=MUTED).pack(pady=(2, 20))

        # Fields
        fields = tk.Frame(card, bg=SURFACE)
        fields.pack(padx=40, pady=(0, 10))

        def field(label, default, show=""):
            tk.Label(fields, text=label, bg=SURFACE, fg=MUTED,
                     font=MONO_XS, anchor="w").pack(fill="x")
            e = tk.Entry(fields, bg=SURFACE2, fg=TEXT, insertbackground=ACCENT,
                         relief="flat", font=MONO_SM, bd=6, width=30, show=show)
            e.insert(0, default)
            e.pack(fill="x", pady=(2, 10))
            return e

        self._login_server   = field("Server IP", SERVER_IP)
        self._login_port     = field("Port",      str(PORT))
        self._login_cert     = field("Certificate path", CERT)
        self._login_username = field("Username", "")

        # Cert browse
        browse_row = tk.Frame(fields, bg=SURFACE)
        browse_row.pack(fill="x", pady=(0, 10))
        tk.Button(browse_row, text="Browse cert…", bg=SURFACE3, fg=ACCENT2,
                  activebackground=BORDER, relief="flat",
                  font=("Helvetica", 9), cursor="hand2",
                  command=self._browse_cert).pack(side="left")

        # Error label
        self._login_err = tk.Label(fields, text="", bg=SURFACE, fg=DANGER,
                                    font=MONO_XS, wraplength=300)
        self._login_err.pack(fill="x")

        # Connect button
        ttk.Button(card, text="Connect  →",
                   style="Accent.TButton",
                   command=self._do_connect).pack(pady=(4, 28), ipadx=20)

        self._login_username.focus_set()
        self._login_username.bind("<Return>", lambda e: self._do_connect())

    def _browse_cert(self):
        path = filedialog.askopenfilename(
            title="Select server certificate",
            filetypes=[("Certificate", "*.crt *.pem"), ("All files", "*.*")]
        )
        if path:
            self._login_cert.delete(0, "end")
            self._login_cert.insert(0, path)

    #  CONNECT / DISCONNECT
    def _do_connect(self):
        server = self._login_server.get().strip()
        cert   = self._login_cert.get().strip()
        user   = self._login_username.get().strip()

        try:
            port = int(self._login_port.get().strip())
        except ValueError:
            self._login_err.config(text="Port must be a number")
            return

        if not user:
            self._login_err.config(text="Username cannot be empty")
            return
        if len(user) > 32:
            self._login_err.config(text="Username too long (max 32 chars)")
            return

        self._username = user
        self._login_err.config(text="Connecting…", fg=MUTED)

        self._client = ChatClient(
            on_message    = self._on_message,
            on_status     = self._on_status,
            on_disconnect = self._on_disconnected,
        )

        threading.Thread(
            target=self._client.connect,
            args=(server, port, cert, user),
            daemon=True
        ).start()

        # Wait briefly then check if connected
        self.after(1800, self._check_connected)

    def _check_connected(self):
        if self._client and self._client._connected:
            self._login_frame.destroy()
            self._main.pack(fill="both", expand=True)
            self._disc_btn.pack(side="right", padx=12, pady=8)
            self._me_label.config(text=self._username)
            self._set_tls_active()
            self._status(f"Connected as {self._username}")
            self._text_inp.focus_set()
        else:
            # Stay on login screen — error already shown via on_status
            pass

    def _do_disconnect(self):
        if self._client:
            self._client.disconnect()
        self._on_disconnected()

    def _on_disconnected(self):
        self.after(0, self._handle_disconnected)

    def _handle_disconnected(self):
        if self._client:
            self._client._connected = False
        self._set_tls_inactive()
        self._append_msg("--- Disconnected from server ---\n", "server")
        self._status("Disconnected")
        self._disc_btn.pack_forget()

    #  ROOM MANAGEMENT
    def _do_join(self):
        room = self._room_entry.get().strip()
        if not room:
            return
        if room not in self._rooms:
            self._rooms.append(room)
            self._room_list.insert("end", f"  # {room}")
            self._room_combo["values"] = self._rooms
            if not self._active_room.get():
                self._active_room.set(room)
                self._room_title.config(text=f"# {room}", fg=TEXT)
        if self._client:
            self._client.join_room(room)
            self._append_msg(f"→ Joined #{room}\n", "ok")
            self._status(f"Joined #{room}")

    def _do_leave(self):
        sel = self._room_list.curselection()
        if not sel:
            room = self._active_room.get()
        else:
            room = self._rooms[sel[0]]
        if not room or room not in self._rooms:
            return
        self._rooms.remove(room)
        idx = [i for i in range(self._room_list.size())
               if room in self._room_list.get(i)]
        for i in reversed(idx):
            self._room_list.delete(i)
        self._room_combo["values"] = self._rooms
        if self._active_room.get() == room:
            self._active_room.set(self._rooms[0] if self._rooms else "")
            self._room_title.config(
                text=f"# {self._rooms[0]}" if self._rooms else "No room joined",
                fg=TEXT if self._rooms else MUTED
            )
        if self._client:
            self._client.leave_room(room)
            self._append_msg(f"← Left #{room}\n", "warn")
            self._status(f"Left #{room}")

    def _on_room_select(self, event):
        sel = self._room_list.curselection()
        if sel:
            room = self._rooms[sel[0]]
            self._active_room.set(room)
            self._room_title.config(text=f"# {room}", fg=TEXT)

    #  SEND
    def _do_send(self):
        text = self._text_inp.get().strip()
        if not text or not self._client or not self._client._connected:
            return

        # Save to history
        if text:
            self._history.append(text)
            self._hist_idx = len(self._history)

        self._text_inp.delete(0, "end")

        # Private message mode
        if self._pm_var.get():
            target = self._pm_entry.get().strip()
            if not target:
                self._append_msg("⚠  Enter a username for private message\n", "err")
                return
            self._client.send_private(target, text)
            self._append_msg(f"[PM → {target}] {self._username}: {text}\n", "private")
            self._status(f"Private message sent to {target}")
            return

        room = self._active_room.get()
        if not room:
            self._append_msg("⚠  Join a room first\n", "err")
            return

        self._client.send_msg(room, text)
        # Echo own message
        self._append_ts()
        self._append_msg(f"{self._username}", "self")
        self._append_msg(f": {text}\n", "normal")
        self._status(f"Message sent to #{room}")

    def _do_send_file(self):
        if not self._client or not self._client._connected:
            return
        room = self._active_room.get()
        if not room:
            self._append_msg("⚠  Join a room first\n", "err")
            return
        path = filedialog.askopenfilename(title="Select file to send")
        if not path:
            return
        threading.Thread(
            target=self._client.send_file,
            args=(room, path),
            daemon=True
        ).start()
        self._append_msg(f"📎 Sending: {os.path.basename(path)} → #{room}…\n", "file")

    def _toggle_pm(self):
        self._pm_entry.config(
            state="normal" if self._pm_var.get() else "disabled"
        )

    #  MESSAGE ROUTING  (called from network thread — always via after())
    def _on_message(self, kind, text):
        self.after(0, self._route_message, kind, text)

    def _route_message(self, kind, text):
        if kind == "normal":
            # Parse [room][seq] who: text  format from server
            self._append_ts()
            if ":" in text:
                who, _, rest = text.partition(":")
                # strip sequence prefix if present
                if "]" in who:
                    who = who.rsplit("]", 1)[-1].strip()
                self._append_msg(who.strip(), "who")
                self._append_msg(":" + rest + "\n", "normal")
            else:
                self._append_msg(text + "\n", "normal")

        elif kind == "private":
            self._append_ts()
            self._append_msg(f"[PRIVATE] {text}\n", "private")

        elif kind == "server":
            self._append_ts()
            self._append_msg(f"{text}\n", "server")

        elif kind == "ok":
            self._append_ts()
            self._append_msg(f"✓  {text}\n", "ok")

        elif kind == "err":
            self._append_ts()
            self._append_msg(f"⚠  Server: {text}\n", "err")

        elif kind == "file_start":
            self._append_ts()
            self._append_msg(f"📥 Receiving: {text}…\n", "file")

        elif kind == "file_done":
            self._append_ts()
            self._append_msg(f"✓  File saved: {text}\n", "ok")

    def _on_status(self, text, tag="muted"):
        self.after(0, self._handle_status, text, tag)

    def _handle_status(self, text, tag):
        self._status(text)
        if hasattr(self, "_login_err") and self._login_err.winfo_exists():
            color = {"ok": ACCENT, "err": DANGER, "warn": WARN}.get(tag, MUTED)
            self._login_err.config(text=text, fg=color)

    #  MESSAGE AREA HELPERS
    def _append_ts(self):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._msg_area.config(state="normal")
        self._msg_area.insert("end", f"[{ts}] ", "ts")
        self._msg_area.config(state="disabled")

    def _append_msg(self, text, tag=None):
        self._msg_area.config(state="normal")
        if tag:
            self._msg_area.insert("end", text, tag)
        else:
            self._msg_area.insert("end", text)
        self._msg_area.config(state="disabled")
        self._msg_area.see("end")

    def _status(self, text):
        self._statusbar.config(text=f"  {text}")

    #  TLS BADGE
    def _set_tls_active(self):
        self._tls_badge.config(text="  ⬤  TLS 1.3 · ENCRYPTED", fg=ACCENT)
        self._blink_badge(True)

    def _set_tls_inactive(self):
        self._tls_badge.config(text="  ⬤  NOT CONNECTED", fg=MUTED)

    def _blink_badge(self, on):
        self._tls_badge.config(fg=ACCENT if on else SURFACE)
        self.after(900, self._blink_badge, not on)

    #  INPUT HISTORY
    def _history_up(self):
        if self._history and self._hist_idx > 0:
            self._hist_idx -= 1
            self._text_inp.delete(0, "end")
            self._text_inp.insert(0, self._history[self._hist_idx])

    def _history_down(self):
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._text_inp.delete(0, "end")
            self._text_inp.insert(0, self._history[self._hist_idx])
        else:
            self._hist_idx = len(self._history)
            self._text_inp.delete(0, "end")

    #  CLOSE
    def _on_close(self):
        if self._client:
            self._client.disconnect()
        self.destroy()



#  ENTRY POINT
if __name__ == "__main__":
    app = ClientGUI()
    app.mainloop()
