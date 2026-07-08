#!/usr/bin/env python3
"""
Advanced BMI Calculator Application
Features:
- GUI with tkinter (Modern Slate Dark/Light mode theme)
- Input validation (Metric / Imperial with conversion and physiological sanity checks)
- BMI calculation and classification with ideal weight recommendation
- Custom animated Canvas BMI gauge
- Multi-user support with SQLite database (CRUD: Add User, Cascade Delete User)
- Historical data storage, Treeview table view, Delete Record capability
- Interactive dashboard trend visualization with Matplotlib (shaded ranges, auto-theme matching)
- CSV history data export
- Professional error handling
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime
import os
import math
import csv

# Color palettes for modern Light and Dark modes
THEMES = {
    "light": {
        "bg": "#f1f5f9",           # Slate 100
        "card_bg": "#ffffff",      # White
        "fg": "#0f172a",           # Slate 900
        "sub_fg": "#475569",       # Slate 600
        "accent": "#4f46e5",       # Indigo 600
        "accent_hover": "#4338ca", # Indigo 700
        "border": "#cbd5e1",       # Slate 300
        "gauge_bg": "#f8fafc",     # Slate 50
        "plot_bg": "#ffffff",
        "plot_grid": "#e2e8f0",
        "plot_text": "#334155",
    },
    "dark": {
        "bg": "#0f172a",           # Slate 900
        "card_bg": "#1e293b",      # Slate 800
        "fg": "#f8fafc",           # Slate 50
        "sub_fg": "#94a3b8",       # Slate 400
        "accent": "#6366f1",       # Indigo 400
        "accent_hover": "#4f46e5", # Indigo 500
        "border": "#334155",       # Slate 700
        "gauge_bg": "#1e293b",     # Slate 800
        "plot_bg": "#1e293b",
        "plot_grid": "#334155",
        "plot_text": "#94a3b8",
    }
}

# BMI classifications
BMI_CLASSES = [
    {"name": "Underweight", "min": 0, "max": 18.5, "color": "#3b82f6", "desc": "Below healthy range"},
    {"name": "Normal", "min": 18.5, "max": 25.0, "color": "#10b981", "desc": "Healthy weight"},
    {"name": "Overweight", "min": 25.0, "max": 30.0, "color": "#f59e0b", "desc": "Above healthy range"},
    {"name": "Obese", "min": 30.0, "max": 100.0, "color": "#ef4444", "desc": "Significantly above healthy range"}
]


class BMIGauge(tk.Canvas):
    """Custom drawing widget for displaying an animated semi-circular gauge."""
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('width', 300)
        kwargs.setdefault('height', 160)
        kwargs.setdefault('highlightthickness', 0)
        super().__init__(parent, **kwargs)
        self.current_bmi = 10.0
        self.target_bmi = 10.0
        self.theme = None
        self.bind("<Configure>", lambda e: self.draw())

    def set_theme(self, theme):
        self.theme = theme
        self.draw()

    def set_bmi(self, bmi):
        self.target_bmi = max(10.0, min(40.0, bmi))
        self.animate_needle()

    def animate_needle(self):
        diff = self.target_bmi - self.current_bmi
        if abs(diff) < 0.05:
            self.current_bmi = self.target_bmi
            self.draw()
        else:
            self.current_bmi += diff * 0.15  # Smooth ease-out interpolation
            self.draw()
            self.after(20, self.animate_needle)

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Center coordinates
        cx = w / 2
        cy = h - 20
        r = min(w / 2 - 35, h - 35)
        
        if r <= 0:
            return

        # Background color
        bg_color = self.theme["card_bg"] if self.theme else "#ffffff"
        self.configure(bg=bg_color)

        # Draw segmented arcs (mapped BMI 10 to 40)
        # Arc 1: Underweight (<18.5) -> BMI 10 to 18.5 (extent = - (8.5/30)*180 = -51)
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=180, extent=-51, 
                        style='arc', outline="#3b82f6", width=18, tags="gauge")
        # Arc 2: Normal (18.5–25) -> BMI 18.5 to 25 (extent = - (6.5/30)*180 = -39)
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=129, extent=-39, 
                        style='arc', outline="#10b981", width=18, tags="gauge")
        # Arc 3: Overweight (25–30) -> BMI 25 to 30 (extent = - (5/30)*180 = -30)
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=-30, 
                        style='arc', outline="#f59e0b", width=18, tags="gauge")
        # Arc 4: Obese (>=30) -> BMI 30 to 40 (extent = - (10/30)*180 = -60)
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=60, extent=-60, 
                        style='arc', outline="#ef4444", width=18, tags="gauge")

        # Labels color
        text_color = self.theme["fg"] if self.theme else "#1f2937"
        
        # Lower and upper labels
        self.create_text(cx - r - 16, cy, text="10", fill=text_color, font=("Segoe UI", 9, "bold"))
        self.create_text(cx + r + 16, cy, text="40+", fill=text_color, font=("Segoe UI", 9, "bold"))

        # Category thresholds labels
        for val, label in [(18.5, "18.5"), (25.0, "25"), (30.0, "30")]:
            theta = math.radians(180 - (val - 10) / 30 * 180)
            lx = cx + (r + 18) * math.cos(theta)
            ly = cy - (r + 18) * math.sin(theta)
            self.create_text(lx, ly, text=label, fill=text_color, font=("Segoe UI", 8))

        # Draw needle
        bmi_clamped = max(10.0, min(40.0, self.current_bmi))
        angle_rad = math.radians(180 - (bmi_clamped - 10) / 30 * 180)
        
        # Sleek needle drawing
        nx = cx + (r - 8) * math.cos(angle_rad)
        ny = cy - (r - 8) * math.sin(angle_rad)
        
        needle_color = self.theme["fg"] if self.theme else "#0f172a"
        self.create_line(cx, cy, nx, ny, fill=needle_color, width=3, arrow=tk.LAST, arrowshape=(10,12,4))
        
        # Center needle pin
        self.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=needle_color, outline=bg_color, width=2)


class BMICalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraBMI - Premium Health Suite")
        self.root.geometry("1080x700")
        self.root.minsize(980, 640)
        
        # Default Theme and Unit values
        self.theme_var = tk.StringVar(value="light")
        self.unit_var = tk.StringVar(value="metric")
        
        # Database Connection
        self.conn = None
        self.cursor = None
        self.init_database()
        
        # Variables for inputs
        self.user_var = tk.StringVar()
        self.weight_kg_var = tk.StringVar()
        self.height_cm_var = tk.StringVar()
        self.weight_lbs_var = tk.StringVar()
        self.height_ft_var = tk.StringVar()
        self.height_in_var = tk.StringVar()

        # Build UI Components
        self.create_widgets()
        self.load_users()
        
        # Set theme initial state
        self.apply_theme()

    def init_database(self):
        """Initializes SQLite database connection and schemas."""
        db_path = os.path.join(os.path.dirname(__file__), 'bmi_records.db')
        try:
            self.conn = sqlite3.connect(db_path)
            # Ensure foreign key support is enabled
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()

            # Create users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create bmi_records table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    weight REAL NOT NULL, -- always stored in kg
                    height REAL NOT NULL, -- always stored in meters
                    bmi REAL NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Initialization Error", 
                                 f"Failed to connect or set up database: {e}\nApp will run without persistence.")

    def create_widgets(self):
        """Builds the main dashboard grid structure."""
        # Top Header Bar (Global Controls)
        header_bar = ttk.Frame(self.root, padding=(20, 10))
        header_bar.pack(side=tk.TOP, fill=tk.X)
        
        title_lbl = ttk.Label(header_bar, text="AuraBMI Dashboard", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(side=tk.LEFT)
        
        # Theme toggle (Light/Dark)
        theme_btn_light = ttk.Radiobutton(header_bar, text="☀️ Light", variable=self.theme_var, value="light", command=self.apply_theme)
        theme_btn_light.pack(side=tk.RIGHT, padx=5)
        theme_btn_dark = ttk.Radiobutton(header_bar, text="🌙 Dark", variable=self.theme_var, value="dark", command=self.apply_theme)
        theme_btn_dark.pack(side=tk.RIGHT, padx=5)

        # Main Workspace Container
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns (Left side is 420px, right side handles the rest)
        main_container.columnconfigure(0, weight=0, minsize=420)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # LEFT COLUMN (Input & Output metrics)
        left_col = ttk.Frame(main_container)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # 1. User Manager Card
        user_card = ttk.Frame(left_col, style="Card.TFrame", padding=12)
        user_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(user_card, text="USER PROFILE", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
        
        self.user_combo = ttk.Combobox(user_card, textvariable=self.user_var, state="readonly")
        self.user_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.user_combo.bind("<<ComboboxSelected>>", self.on_user_changed)
        
        add_user_btn = ttk.Button(user_card, text="Add Profile", command=self.add_user_dialog)
        add_user_btn.grid(row=2, column=0, sticky="ew", padx=(0, 4))
        
        del_user_btn = ttk.Button(user_card, text="Delete Profile", command=self.delete_user)
        del_user_btn.grid(row=2, column=1, sticky="ew", padx=(4, 0))
        
        user_card.columnconfigure(0, weight=1)
        user_card.columnconfigure(1, weight=1)

        # 2. Input Metrics Card
        input_card = ttk.Frame(left_col, style="Card.TFrame", padding=15)
        input_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(input_card, text="MEASUREMENTS", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 8))
        
        # Unit Toggle
        units_frame = ttk.Frame(input_card)
        units_frame.pack(fill=tk.X, pady=(0, 10))
        
        metric_rdo = ttk.Radiobutton(units_frame, text="Metric (kg/cm)", variable=self.unit_var, value="metric", command=self.on_unit_toggle)
        metric_rdo.pack(side=tk.LEFT, expand=True)
        imperial_rdo = ttk.Radiobutton(units_frame, text="Imperial (lbs/ft)", variable=self.unit_var, value="imperial", command=self.on_unit_toggle)
        imperial_rdo.pack(side=tk.LEFT, expand=True)

        # Dual Input Subpanels
        self.input_subpanel_metric = ttk.Frame(input_card)
        self.input_subpanel_imperial = ttk.Frame(input_card)
        
        # Metric layout
        ttk.Label(self.input_subpanel_metric, text="Height (cm)").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.input_subpanel_metric, textvariable=self.height_cm_var).grid(row=0, column=1, sticky="ew", pady=2, padx=(10, 0))
        ttk.Label(self.input_subpanel_metric, text="Weight (kg)").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.input_subpanel_metric, textvariable=self.weight_kg_var).grid(row=1, column=1, sticky="ew", pady=2, padx=(10, 0))
        self.input_subpanel_metric.columnconfigure(1, weight=1)

        # Imperial layout
        ttk.Label(self.input_subpanel_imperial, text="Height").grid(row=0, column=0, sticky=tk.W, pady=2)
        imp_height_f = ttk.Frame(self.input_subpanel_imperial)
        imp_height_f.grid(row=0, column=1, sticky="ew", pady=2, padx=(10, 0))
        ttk.Entry(imp_height_f, textvariable=self.height_ft_var, width=5).pack(side=tk.LEFT)
        ttk.Label(imp_height_f, text="ft").pack(side=tk.LEFT, padx=(2, 10))
        ttk.Entry(imp_height_f, textvariable=self.height_in_var, width=5).pack(side=tk.LEFT)
        ttk.Label(imp_height_f, text="in").pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.input_subpanel_imperial, text="Weight (lbs)").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.input_subpanel_imperial, textvariable=self.weight_lbs_var).grid(row=1, column=1, sticky="ew", pady=2, padx=(10, 0))
        self.input_subpanel_imperial.columnconfigure(1, weight=1)

        # Pack metric by default
        self.input_subpanel_metric.pack(fill=tk.X, pady=(0, 10))

        # Main action button
        self.calc_btn = ttk.Button(input_card, text="Calculate & Save BMI", style="Action.TButton", command=self.calculate_bmi)
        self.calc_btn.pack(fill=tk.X, ipady=4)

        # 3. Results Feedback Card
        self.results_card = ttk.Frame(left_col, style="Card.TFrame", padding=15)
        self.results_card.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.results_card, text="ANALYSIS", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        
        stats_frame = ttk.Frame(self.results_card)
        stats_frame.pack(fill=tk.X, pady=8)
        
        self.bmi_num_lbl = ttk.Label(stats_frame, text="--.-", font=("Segoe UI", 28, "bold"), foreground="#4f46e5")
        self.bmi_num_lbl.pack(anchor=tk.CENTER)
        
        self.category_lbl = ttk.Label(stats_frame, text="No Analysis Yet", font=("Segoe UI", 12, "bold"))
        self.category_lbl.pack(anchor=tk.CENTER, pady=2)
        
        self.ideal_lbl = ttk.Label(stats_frame, text="Select a user and input details.", font=("Segoe UI", 9), foreground="#64748b")
        self.ideal_lbl.pack(anchor=tk.CENTER)

        # Animated Semi-circle Gauge
        self.gauge = BMIGauge(self.results_card)
        self.gauge.pack(fill=tk.X, pady=(5, 0), expand=True)


        # RIGHT COLUMN (Visual chart and detailed history logging)
        right_col = ttk.Frame(main_container)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # 1. Trend Chart Card
        chart_card = ttk.Frame(right_col, style="Card.TFrame", padding=15)
        chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Configure embedded matplotlib canvas
        self.fig, self.ax = plt.subplots(figsize=(6, 3), dpi=100)
        self.fig.patch.set_facecolor("#ffffff")
        self.ax.set_facecolor("#ffffff")
        
        self.chart_canvas = FigureCanvasTkAgg(self.fig, chart_card)
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 2. History Summary Card
        history_summary_card = ttk.Frame(right_col, style="Card.TFrame", padding=12)
        history_summary_card.pack(fill=tk.X)
        
        ttk.Label(history_summary_card, text="RECENT LOGS", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        # Quick View Treeview
        columns = ("date", "bmi", "weight", "category")
        self.recent_tree = ttk.Treeview(history_summary_card, columns=columns, show="headings", height=3)
        self.recent_tree.heading("date", text="Date")
        self.recent_tree.heading("bmi", text="BMI")
        self.recent_tree.heading("weight", text="Weight")
        self.recent_tree.heading("category", text="Category")
        
        self.recent_tree.column("date", width=120, anchor=tk.W)
        self.recent_tree.column("bmi", width=60, anchor=tk.CENTER)
        self.recent_tree.column("weight", width=80, anchor=tk.CENTER)
        self.recent_tree.column("category", width=100, anchor=tk.CENTER)
        
        self.recent_tree.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        # Actions for history
        view_all_btn = ttk.Button(history_summary_card, text="Manage History", command=self.open_history_window)
        view_all_btn.grid(row=2, column=0, sticky="ew", padx=(0, 4))
        
        export_btn = ttk.Button(history_summary_card, text="Export CSV", command=self.export_csv)
        export_btn.grid(row=2, column=1, sticky="ew", padx=(4, 0))
        
        history_summary_card.columnconfigure(0, weight=1)
        history_summary_card.columnconfigure(1, weight=1)

        # Status Bar at Bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(10, 3))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_users(self):
        """Loads registered users from SQLite database."""
        if not self.conn:
            return
        try:
            self.cursor.execute("SELECT name FROM users ORDER BY name")
            users = [row[0] for row in self.cursor.fetchall()]
            self.user_combo['values'] = users
            if users:
                # Default to first user
                self.user_combo.current(0)
                self.on_user_changed()
            else:
                self.user_var.set("")
                self.redraw_trend_chart()
                self.clear_recent_table()
        except sqlite3.Error as e:
            messagebox.showerror("Database Query Error", f"Could not retrieve user profiles: {e}")

    def on_user_changed(self, event=None):
        """Fires when user profiles dropdown is selected."""
        user = self.user_var.get()
        if user:
            self.status_var.set(f"Active Profile: {user}")
            self.redraw_trend_chart()
            self.load_recent_logs()
            self.clear_results_feedback()
        else:
            self.clear_recent_table()

    def on_unit_toggle(self):
        """Handles switching metric/imperial input fields dynamically."""
        if self.unit_var.get() == "metric":
            self.input_subpanel_imperial.pack_forget()
            self.input_subpanel_metric.pack(fill=tk.X, pady=(0, 10))
        else:
            self.input_subpanel_metric.pack_forget()
            self.input_subpanel_imperial.pack(fill=tk.X, pady=(0, 10))

    def add_user_dialog(self):
        """Creates a popup window to save a new named user."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create User Profile")
        dialog.geometry("300x130")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center relative to parent
        dialog.geometry(f"+{self.root.winfo_x() + 300}+{self.root.winfo_y() + 200}")
        
        theme = THEMES[self.theme_var.get()]
        dialog.configure(bg=theme["bg"])
        
        lbl = tk.Label(dialog, text="Enter Profile Name:", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10))
        lbl.pack(pady=(12, 4))
        
        name_entry = tk.Entry(dialog, bg=theme["card_bg"], fg=theme["fg"], insertbackground=theme["fg"], highlightthickness=1)
        name_entry.pack(pady=4, padx=20, fill=tk.X)
        name_entry.focus()
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Validation Error", "Name field cannot be left blank.")
                return
            if len(name) > 30:
                messagebox.showwarning("Validation Error", "Name is too long. Limit is 30 characters.")
                return
            try:
                self.cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
                self.conn.commit()
                dialog.destroy()
                self.load_users()
                # Auto-select the newly added user
                self.user_combo.set(name)
                self.on_user_changed()
                messagebox.showinfo("Profile Created", f"Successfully registered user profile '{name}'.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Conflict Error", "A user profile with this name already exists.")
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not create user profile: {e}")
                
        btn_frame = tk.Frame(dialog, bg=theme["bg"])
        btn_frame.pack(pady=12)
        
        # Custom button configs manually for Toplevel
        save_btn = tk.Button(btn_frame, text="Create", width=10, bg=theme["accent"], fg="white", activebackground=theme["accent_hover"], activeforeground="white", command=save)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, bg=theme["border"], fg=theme["fg"], activebackground=theme["bg"], activeforeground=theme["fg"], command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        name_entry.bind("<Return>", lambda e: save())

    def delete_user(self):
        """Safely cascade deletes the selected user profile and its records."""
        user = self.user_var.get()
        if not user:
            messagebox.showerror("Profile Selection Required", "Please select a user profile to delete.")
            return
            
        confirm = messagebox.askyesno(
            "Delete Confirmation",
            f"Are you sure you want to permanently delete profile '{user}'?\n"
            "This will remove ALL their historical BMI data logs from database.",
            icon='warning'
        )
        if not confirm:
            return
            
        try:
            # We perform manual cascade fallback safety check alongside FK CASCADE
            self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
            user_id = self.cursor.fetchone()[0]
            
            self.cursor.execute("DELETE FROM bmi_records WHERE user_id = ?", (user_id,))
            self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            
            self.status_var.set(f"Deleted profile: {user}")
            self.load_users()
        except sqlite3.Error as e:
            messagebox.showerror("Database Query Failure", f"Could not delete user: {e}")

    def validate_inputs(self):
        """Robust multi-unit validation checks. Returns (weight_kg, height_m) or None."""
        unit = self.unit_var.get()
        try:
            if unit == "metric":
                h_str = self.height_cm_var.get().strip()
                w_str = self.weight_kg_var.get().strip()
                
                if not h_str or not w_str:
                    raise ValueError("All height and weight measurements are required.")
                    
                height_cm = float(h_str)
                weight_kg = float(w_str)
                
                if height_cm <= 0 or weight_kg <= 0:
                    raise ValueError("Measurements must be positive numbers greater than 0.")
                    
                # Physiological boundary limits check
                if not (30.0 <= height_cm <= 300.0):
                    raise ValueError("Height must fall between 30 and 300 centimeters.")
                if not (2.0 <= weight_kg <= 600.0):
                    raise ValueError("Weight must fall between 2.0 and 600.0 kilograms.")
                    
                return weight_kg, height_cm / 100.0
                
            else: # Imperial unit
                ft_str = self.height_ft_var.get().strip()
                in_str = self.height_in_var.get().strip()
                w_str = self.weight_lbs_var.get().strip()
                
                if not ft_str or not in_str or not w_str:
                    raise ValueError("Please fill in feet, inches, and pounds fields.")
                    
                height_ft = float(ft_str)
                height_in = float(in_str)
                weight_lbs = float(w_str)
                
                if height_ft < 0 or height_in < 0 or weight_lbs <= 0:
                    raise ValueError("Measurements must be positive values.")
                if height_ft == 0 and height_in == 0:
                    raise ValueError("Height must be at least 1 inch.")
                    
                total_inches = (height_ft * 12.0) + height_in
                
                # Physiological boundary limits check
                if not (12.0 <= total_inches <= 120.0):
                    raise ValueError("Height must fall between 1 ft 0 in (12 in) and 10 ft 0 in (120 in).")
                if not (4.0 <= weight_lbs <= 1300.0):
                    raise ValueError("Weight must fall between 4.0 and 1300.0 pounds.")
                    
                # Standard conversions
                weight_kg = weight_lbs * 0.45359237
                height_m = total_inches * 0.0254
                return weight_kg, height_m
                
        except ValueError as err:
            # Handle empty/non-numeric conversion errors specifically
            msg = str(err)
            if "could not convert string to float" in msg:
                msg = "Measurements must contain numbers only."
            messagebox.showerror("Measurement Entry Error", msg)
            return None

    def calculate_bmi(self):
        """Performs calculation, updates needle gauge, ideal range, and database logs."""
        user = self.user_var.get()
        if not user:
            messagebox.showerror("User Profile Required", "Please select or create a user profile before running calculations.")
            return

        validated = self.validate_inputs()
        if not validated:
            return
            
        weight_kg, height_m = validated
        
        # Formula: weight (kg) / height^2 (m)
        bmi = weight_kg / (height_m ** 2)
        
        # Classification Mapping
        category = "Obese"
        color = "#ef4444"
        for classification in BMI_CLASSES:
            if classification["min"] <= bmi < classification["max"]:
                category = classification["name"]
                color = classification["color"]
                break
                
        # Ideal Weight Calculation (Normal BMI: 18.5 - 24.9)
        min_ideal_kg = 18.5 * (height_m ** 2)
        max_ideal_kg = 24.9 * (height_m ** 2)
        
        # Unit preference for display
        if self.unit_var.get() == "metric":
            ideal_range_text = f"Ideal Range: {min_ideal_kg:.1f} - {max_ideal_kg:.1f} kg"
        else:
            min_ideal_lbs = min_ideal_kg * 2.20462
            max_ideal_lbs = max_ideal_kg * 2.20462
            ideal_range_text = f"Ideal Range: {min_ideal_lbs:.1f} - {max_ideal_lbs:.1f} lbs"

        # Update Display Cards
        self.bmi_num_lbl.configure(text=f"{bmi:.2f}", foreground=color)
        self.category_lbl.configure(text=category, foreground=color)
        self.ideal_lbl.configure(text=ideal_range_text)
        
        # Move gauge pointer needle
        self.gauge.set_bmi(bmi)

        # Persistence to SQLite database
        try:
            self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
            user_id = self.cursor.fetchone()[0]
            
            # Save record (always keep raw base metrics metric)
            self.cursor.execute('''
                INSERT INTO bmi_records (user_id, weight, height, bmi, category)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, weight_kg, height_m, bmi, category))
            self.conn.commit()
            
            self.status_var.set(f"Saved logs for {user} - BMI: {bmi:.2f}")
            
            # Refresh visualization systems
            self.load_recent_logs()
            self.redraw_trend_chart()
        except sqlite3.Error as e:
            messagebox.showerror("Persistence Database Error", f"Calculation completed but could not save record: {e}")

    def load_recent_logs(self):
        """Fills dashboard's mini summary table with the latest 3 calculations."""
        self.clear_recent_table()
        user = self.user_var.get()
        if not user or not self.conn:
            return
            
        try:
            self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
            user_id = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT timestamp, bmi, weight, category
                FROM bmi_records
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 3
            ''', (user_id,))
            
            rows = self.cursor.fetchall()
            for row in rows:
                raw_time, bmi, weight_kg, category = row
                # Format ISO/Standard Timestamp
                dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%b %d, %H:%M")
                
                # Weight display logic based on active unit toggle
                if self.unit_var.get() == "metric":
                    weight_display = f"{weight_kg:.1f} kg"
                else:
                    weight_display = f"{(weight_kg * 2.20462):.1f} lbs"
                    
                self.recent_tree.insert("", tk.END, values=(date_str, f"{bmi:.1f}", weight_display, category))
        except sqlite3.Error as e:
            self.status_var.set(f"Error loading history tables: {e}")

    def redraw_trend_chart(self):
        """Refreshes the Matplotlib plot layout based on historical database logs."""
        self.ax.clear()
        
        theme = THEMES[self.theme_var.get()]
        
        # Color matching settings
        self.fig.patch.set_facecolor(theme["card_bg"])
        self.ax.set_facecolor(theme["card_bg"])
        
        # Axis lines colors
        self.ax.tick_params(colors=theme["plot_text"], labelsize=8)
        self.ax.xaxis.label.set_color(theme["plot_text"])
        self.ax.yaxis.label.set_color(theme["plot_text"])
        self.ax.title.set_color(theme["plot_text"])
        
        for name, spine in self.ax.spines.items():
            spine.set_color(theme["border"])
            
        user = self.user_var.get()
        if not user:
            self.ax.text(0.5, 0.5, "Create or Select a User Profile", 
                         ha='center', va='center', color=theme["sub_fg"], fontsize=10)
            self.chart_canvas.draw()
            return
            
        try:
            self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
            user_res = self.cursor.fetchone()
            if not user_res:
                self.chart_canvas.draw()
                return
            user_id = user_res[0]
            
            self.cursor.execute('''
                SELECT bmi, timestamp
                FROM bmi_records
                WHERE user_id = ?
                ORDER BY timestamp ASC
            ''', (user_id,))
            records = self.cursor.fetchall()
            
            if not records:
                self.ax.text(0.5, 0.5, "No history logs yet.\nPerform measurements to plot trend.", 
                             ha='center', va='center', color=theme["sub_fg"], fontsize=9)
                self.chart_canvas.draw()
                return
                
            bmis = [r[0] for r in records]
            dates = [datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") for r in records]
            
            # Plot the line trend
            self.ax.plot(dates, bmis, color=theme["accent"], marker='o', linewidth=2.5, markersize=5, label='User BMI')
            
            # Colored background bands representing categories
            self.ax.axhspan(18.5, 25.0, color='#10b981', alpha=0.1, label='Healthy Range (18.5-25)')
            self.ax.axhline(18.5, color='#3b82f6', linestyle='--', alpha=0.4, linewidth=1)
            self.ax.axhline(25.0, color='#f59e0b', linestyle='--', alpha=0.4, linewidth=1)
            self.ax.axhline(30.0, color='#ef4444', linestyle='--', alpha=0.4, linewidth=1)
            
            self.ax.grid(True, color=theme["plot_grid"], linestyle=':', alpha=0.6)
            self.ax.set_title(f"BMI History Trend for {user}", fontsize=11, fontweight='bold', pad=8)
            self.ax.set_ylabel("BMI Value", fontsize=8)
            
            # Format date formatting on axes ticks
            self.fig.autofmt_xdate(bottom=0.22, rotation=25)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            
            # Legends styling
            legend = self.ax.legend(facecolor=theme["card_bg"], edgecolor=theme["border"], fontsize=7, loc='upper left')
            if legend:
                for text in legend.get_texts():
                    text.set_color(theme["plot_text"])
                    
            # Auto-scale Y window bounds comfortably
            y_min = min(bmis) - 2.5
            y_max = max(bmis) + 2.5
            self.ax.set_ylim(max(8, y_min), min(48, y_max))
            
        except sqlite3.Error:
            self.ax.text(0.5, 0.5, "Data plotting failure.", ha='center', va='center', color="#ef4444")
            
        self.chart_canvas.draw()

    def open_history_window(self):
        """Creates a popup window displaying the full list of BMI logs with CRUD controls."""
        user = self.user_var.get()
        if not user:
            messagebox.showerror("Profile Selection Required", "Please select a user profile to manage records.")
            return
            
        history_win = tk.Toplevel(self.root)
        history_win.title(f"Historical Records: {user}")
        history_win.geometry("640x440")
        history_win.transient(self.root)
        history_win.grab_set()
        
        theme = THEMES[self.theme_var.get()]
        history_win.configure(bg=theme["bg"])
        
        lbl_title = tk.Label(history_win, text=f"Complete History Log - {user}", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 12, "bold"))
        lbl_title.pack(pady=10)

        # Table frame
        tbl_frame = ttk.Frame(history_win)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        cols = ("id", "date", "weight", "height", "bmi", "category")
        tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="browse")
        
        tree.heading("date", text="Date & Time")
        tree.heading("weight", text="Weight")
        tree.heading("height", text="Height")
        tree.heading("bmi", text="BMI")
        tree.heading("category", text="Category")
        
        # Hide internal SQLite identifier
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("id", width=0, stretch=tk.NO)
        tree.column("date", width=140, anchor=tk.W)
        tree.column("weight", width=90, anchor=tk.CENTER)
        tree.column("height", width=90, anchor=tk.CENTER)
        tree.column("bmi", width=70, anchor=tk.CENTER)
        tree.column("category", width=110, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def reload_records():
            tree.delete(*tree.get_children())
            try:
                self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
                u_id = self.cursor.fetchone()[0]
                self.cursor.execute('''
                    SELECT id, timestamp, weight, height, bmi, category
                    FROM bmi_records
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                ''', (u_id,))
                
                for r in self.cursor.fetchall():
                    r_id, stamp, w, h, b, cat = r
                    dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
                    f_stamp = dt.strftime("%Y-%m-%d %H:%M")
                    
                    if self.unit_var.get() == "metric":
                        w_display = f"{w:.1f} kg"
                        h_display = f"{(h * 100):.1f} cm"
                    else:
                        w_display = f"{(w * 2.20462):.1f} lbs"
                        total_in = h / 0.0254
                        h_ft = int(total_in // 12)
                        h_in = int(round(total_in % 12))
                        h_display = f"{h_ft} ft {h_in} in"
                        
                    tree.insert("", tk.END, values=(r_id, f_stamp, w_display, h_display, f"{b:.2f}", cat))
            except sqlite3.Error as e:
                messagebox.showerror("Database Query Error", f"Could not retrieve details: {e}")

        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Selection Required", "Please select a record from the table list to delete.")
                return
            
            confirm = messagebox.askyesno(
                "Confirm Deletion",
                "Are you sure you want to delete this specific BMI measurement record?",
                parent=history_win
            )
            if not confirm:
                return
                
            item_values = tree.item(selected[0], "values")
            record_id = item_values[0] # SQLite table row ID
            
            try:
                self.cursor.execute("DELETE FROM bmi_records WHERE id = ?", (record_id,))
                self.conn.commit()
                self.status_var.set("Deleted BMI log record.")
                reload_records()
                self.load_recent_logs()
                self.redraw_trend_chart()
            except sqlite3.Error as e:
                messagebox.showerror("Database Write Failure", f"Failed to delete record: {e}", parent=history_win)

        # Run load details initially
        reload_records()
        
        # Action Panel
        action_f = tk.Frame(history_win, bg=theme["bg"])
        action_f.pack(fill=tk.X, pady=12)
        
        del_btn = tk.Button(action_f, text="Delete Selected Record", bg="#ef4444", fg="white", activebackground="#dc2626", activeforeground="white", command=delete_selected)
        del_btn.pack(side=tk.LEFT, padx=15)
        
        close_btn = tk.Button(action_f, text="Close Window", bg=theme["border"], fg=theme["fg"], activebackground=theme["bg"], activeforeground=theme["fg"], command=history_win.destroy)
        close_btn.pack(side=tk.RIGHT, padx=15)

    def export_csv(self):
        """Allows exporting a structured history report for selected user to a CSV file."""
        user = self.user_var.get()
        if not user:
            messagebox.showerror("Profile Selection Required", "Please select a user profile to export records.")
            return
            
        try:
            self.cursor.execute("SELECT id FROM users WHERE name = ?", (user,))
            user_id = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT timestamp, weight, height, bmi, category
                FROM bmi_records
                WHERE user_id = ?
                ORDER BY timestamp DESC
            ''', (user_id,))
            records = self.cursor.fetchall()
            
            if not records:
                messagebox.showinfo("Export Empty", f"There are no recorded entries logged for user '{user}' yet.")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV File", "*.csv"), ("All Files", "*.*")],
                title="Export BMI History Report",
                initialfile=f"{user.lower().replace(' ', '_')}_bmi_history.csv"
            )
            
            if not file_path:
                return # user canceled dialouge box
                
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Headings
                writer.writerow(["Timestamp", "Weight (kg)", "Height (m)", "Calculated BMI", "Category"])
                for r in records:
                    writer.writerow(row for row in r)
                    
            messagebox.showinfo("Export Successful", f"Successfully exported history logs of '{user}' to:\n{file_path}")
        except (sqlite3.Error, OSError) as err:
            messagebox.showerror("Export Failure", f"Failed to save CSV file: {err}")

    def apply_theme(self):
        """Recursively updates themed style metrics across all widgets."""
        theme = THEMES[self.theme_var.get()]
        
        # Configure Root Widget Background
        self.root.configure(bg=theme["bg"])
        
        # ttk styles mapping overrides
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        # Basic settings
        style.configure(".", background=theme["bg"], foreground=theme["fg"])
        style.configure("TFrame", background=theme["bg"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        
        # Specialized Card container style
        style.configure("Card.TFrame", background=theme["card_bg"], bordercolor=theme["border"], borderwidth=1, relief="solid")
        
        # Buttons configurations
        style.configure("TButton", background=theme["border"], foreground=theme["fg"], bordercolor=theme["border"], font=("Segoe UI", 9))
        style.map("TButton", 
                  background=[("active", theme["bg"]), ("pressed", theme["border"])],
                  foreground=[("active", theme["accent"])])
                  
        style.configure("Action.TButton", background=theme["accent"], foreground="white", bordercolor=theme["accent"], font=("Segoe UI", 9, "bold"))
        style.map("Action.TButton", 
                  background=[("active", theme["accent_hover"]), ("pressed", theme["accent"])],
                  foreground=[("active", "white")])
                  
        # Combo boxes and Radio styling
        style.configure("TRadiobutton", background=theme["bg"], foreground=theme["fg"])
        style.map("TRadiobutton", background=[("active", theme["bg"])], foreground=[("active", theme["accent"])])
        
        style.configure("TCombobox", fieldbackground=theme["card_bg"], background=theme["bg"], foreground=theme["fg"], bordercolor=theme["border"])
        style.map("TCombobox", fieldbackground=[("readonly", theme["card_bg"])])
        
        # Listbox bindings overrides for dropdown combobox options
        self.root.option_add("*TCombobox*Listbox.background", theme["card_bg"])
        self.root.option_add("*TCombobox*Listbox.foreground", theme["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", theme["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        
        # Styled Treeviews
        style.configure("Treeview", 
                        background=theme["card_bg"], 
                        foreground=theme["fg"], 
                        fieldbackground=theme["card_bg"],
                        rowheight=25,
                        bordercolor=theme["border"],
                        borderwidth=1)
        style.configure("Treeview.Heading", 
                        background=theme["border"], 
                        foreground=theme["fg"], 
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", theme["accent"])], foreground=[("selected", "white")])

        # Traverse and style standard sub-widgets recursively
        self.recursive_theme_update(self.root, theme)
        
        # Refresh visuals
        self.redraw_trend_chart()

    def recursive_theme_update(self, widget, theme):
        """Walks down widget hierarchy to customize underlying elements."""
        w_class = widget.winfo_class()
        
        try:
            if isinstance(widget, BMIGauge):
                widget.set_theme(theme)
            elif w_class == "Frame":
                widget.configure(bg=theme["bg"])
            elif w_class == "Label":
                widget.configure(bg=theme["bg"], fg=theme["fg"])
            elif w_class == "Canvas":
                # Only apply standard background overrides if not the gauge itself
                if not isinstance(widget, BMIGauge):
                    widget.configure(bg=theme["card_bg"], highlightbackground=theme["border"])
            elif isinstance(widget, tk.Entry):
                # Legacy tk entries fallback
                widget.configure(bg=theme["card_bg"], fg=theme["fg"], insertbackground=theme["fg"],
                                 highlightbackground=theme["border"], highlightcolor=theme["accent"])
        except Exception:
            pass # Skip widgets without configurable properties
            
        for child in widget.winfo_children():
            self.recursive_theme_update(child, theme)

    def clear_results_feedback(self):
        """Resets result labels to default values."""
        self.bmi_num_lbl.configure(text="--.-", foreground="#4f46e5")
        self.category_lbl.configure(text="No Analysis Yet", foreground=THEMES[self.theme_var.get()]["fg"])
        self.ideal_lbl.configure(text="Select a user and input details.")
        self.gauge.target_bmi = 10.0
        self.gauge.current_bmi = 10.0
        self.gauge.draw()

    def clear_recent_table(self):
        """Clears all records in dashboard summary table."""
        self.recent_tree.delete(*self.recent_tree.get_children())

    def close_app(self):
        """Clean release of databases connections on exit."""
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = BMICalculator(root)
    
    # Graceful intercept of window close operations
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()


if __name__ == "__main__":
    main()