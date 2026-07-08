#!/usr/bin/env python3
"""
AuraPass - Cryptographically Secure Password Suite
Features:
- GUI with tkinter (Modern Slate Dark/Light mode theme)
- Bidirectionally synced slider and spinbox length controls
- Character pool selection checkboxes (Uppercase, Lowercase, Digits, Symbols)
- Dynamic strength calculation based on Shannon entropy with real-time colored visual bar
- Ambiguous character exclusion option
- Secrets module for cryptographic random generation
- Guaranteed character category representation
- Clipboard integration using pyperclip (automatic copy on generation)
- Session history display (masked passwords, eye icon toggle, direct copy, memory-only)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import secrets
import pyperclip
import math

# Theme Palette configuration matching AuraBMI dashboard
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


def secure_shuffle(lst):
    """Performs an unbiased, cryptographically secure Fisher-Yates shuffle in-place."""
    for i in range(len(lst) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        lst[i], lst[j] = lst[j], lst[i]


class PasswordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraPass - Secure Password Suite")
        self.root.geometry("860x540")
        self.root.minsize(780, 480)

        # Settings variables
        self.theme_var = tk.StringVar(value="light")
        self.length_var = tk.IntVar(value=16)
        
        self.upper_var = tk.BooleanVar(value=True)
        self.lower_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=False)
        self.ambiguous_var = tk.BooleanVar(value=False)

        self.password_output_var = tk.StringVar()
        
        # Session history stores (Memory-only, last 5 items)
        self.history = []
        self.history_visible = []

        # Create GUI layout
        self.create_widgets()
        
        # Attach traces for live interactive visual updates
        self.length_var.trace_add("write", lambda *args: self.update_strength_display())
        self.upper_var.trace_add("write", lambda *args: self.update_strength_display())
        self.lower_var.trace_add("write", lambda *args: self.update_strength_display())
        self.digits_var.trace_add("write", lambda *args: self.update_strength_display())
        self.symbols_var.trace_add("write", lambda *args: self.update_strength_display())
        self.ambiguous_var.trace_add("write", lambda *args: self.update_strength_display())

        # Sync visual theme
        self.apply_theme()
        
        # Draw strength visual bar initially
        self.update_strength_display()

    def create_widgets(self):
        """Builds GUI layout grids."""
        # Top Header Bar
        header_bar = ttk.Frame(self.root, padding=(20, 10))
        header_bar.pack(side=tk.TOP, fill=tk.X)

        title_lbl = ttk.Label(header_bar, text="AuraPass Suite", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(side=tk.LEFT)

        theme_btn_light = ttk.Radiobutton(header_bar, text="☀️ Light", variable=self.theme_var, value="light", command=self.apply_theme)
        theme_btn_light.pack(side=tk.RIGHT, padx=5)
        theme_btn_dark = ttk.Radiobutton(header_bar, text="🌙 Dark", variable=self.theme_var, value="dark", command=self.apply_theme)
        theme_btn_dark.pack(side=tk.RIGHT, padx=5)

        # Main grid container split: Left (Settings), Right (Output & History)
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        main_container.columnconfigure(0, weight=1, minsize=380)
        main_container.columnconfigure(1, weight=1, minsize=380)
        main_container.rowconfigure(0, weight=1)

        # LEFT SIDE PANEL: CONFIGURATIONS CARD
        left_col = ttk.Frame(main_container)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        settings_card = ttk.Frame(left_col, style="Card.TFrame", padding=15)
        settings_card.pack(fill=tk.BOTH, expand=True)

        ttk.Label(settings_card, text="GENERATOR SETTINGS", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Synchronized Length Controls
        length_frame = ttk.Frame(settings_card)
        length_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(length_frame, text="Password Length:").pack(side=tk.LEFT)
        
        # Spinbox
        length_spin = tk.Spinbox(length_frame, from_=8, to=64, textvariable=self.length_var, width=5, justify=tk.CENTER)
        length_spin.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Slider
        length_slider = ttk.Scale(length_frame, from_=8, to=64, variable=self.length_var, orient=tk.HORIZONTAL)
        length_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        # Character Options Frame
        options_frame = ttk.Frame(settings_card)
        options_frame.pack(fill=tk.X, pady=10)

        ttk.Label(options_frame, text="Character Pools (Select at least 2):", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 5))

        ttk.Checkbutton(options_frame, text="Uppercase Letters (A-Z)", variable=self.upper_var).pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(options_frame, text="Lowercase Letters (a-z)", variable=self.lower_var).pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(options_frame, text="Numbers (0-9)", variable=self.digits_var).pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(options_frame, text="Symbols (!@#$...)", variable=self.symbols_var).pack(anchor=tk.W, pady=3)

        # Separator line
        sep = ttk.Separator(settings_card, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=10)

        # Exclusions Frame
        exclude_frame = ttk.Frame(settings_card)
        exclude_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(exclude_frame, text="Exclude Ambiguous Characters\n(e.g., 0, O, o, 1, I, l, |)", variable=self.ambiguous_var).pack(anchor=tk.W)

        # RIGHT SIDE PANEL: GENERATED & HISTORY
        right_col = ttk.Frame(main_container)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 1. Output Metrics Card
        output_card = ttk.Frame(right_col, style="Card.TFrame", padding=15)
        output_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(output_card, text="SECURE PASSWORD GENERATED", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 8))

        # Output entry field
        output_row = ttk.Frame(output_card)
        output_row.pack(fill=tk.X, pady=5)
        
        self.output_entry = tk.Entry(output_row, textvariable=self.password_output_var, font=("Courier New", 12, "bold"),
                                     relief=tk.FLAT, bd=0, state="readonly", justify=tk.CENTER)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 5))
        
        self.copy_btn = ttk.Button(output_row, text="📋 Copy", width=8, command=self.copy_active_password)
        self.copy_btn.pack(side=tk.RIGHT)

        # Strength indicator bar and text
        strength_row = ttk.Frame(output_card)
        strength_row.pack(fill=tk.X, pady=(10, 2))
        
        ttk.Label(strength_row, text="Strength:").pack(side=tk.LEFT)
        self.strength_lbl = ttk.Label(strength_row, text="Calculated Level", font=("Segoe UI", 9, "bold"))
        self.strength_lbl.pack(side=tk.RIGHT)

        self.strength_canvas = tk.Canvas(output_card, height=8, highlightthickness=0)
        self.strength_canvas.pack(fill=tk.X, pady=5)

        # Primary generate action button
        self.generate_btn = ttk.Button(output_card, text="Generate Secure Password", style="Action.TButton", command=self.generate_password)
        self.generate_btn.pack(fill=tk.X, pady=(8, 0), ipady=5)

        # 2. History card
        history_card = ttk.Frame(right_col, style="Card.TFrame", padding=15)
        history_card.pack(fill=tk.BOTH, expand=True)

        ttk.Label(history_card, text="SESSION HISTORY (LAST 5)", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 8))

        self.history_inner_frame = ttk.Frame(history_card)
        self.history_inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Populate history initially
        self.redraw_history()

        # Status strip at bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(10, 3))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def calculate_current_entropy(self):
        """Calculates mathematical Shannon entropy based on options."""
        length = self.length_var.get()
        
        include_upper = self.upper_var.get()
        include_lower = self.lower_var.get()
        include_digits = self.digits_var.get()
        include_symbols = self.symbols_var.get()
        exclude_ambiguous = self.ambiguous_var.get()

        N = 0
        if include_lower:
            N += 24 if exclude_ambiguous else 26
        if include_upper:
            N += 24 if exclude_ambiguous else 26
        if include_digits:
            N += 8 if exclude_ambiguous else 10
        if include_symbols:
            N += 27 if exclude_ambiguous else 28 # '|' is ambiguous

        if N == 0:
            return 0
            
        return length * math.log2(N)

    def update_strength_display(self):
        """Redraws the strength bar indicator and label based on settings."""
        include_upper = self.upper_var.get()
        include_lower = self.lower_var.get()
        include_digits = self.digits_var.get()
        include_symbols = self.symbols_var.get()

        pools_selected = sum([include_upper, include_lower, include_digits, include_symbols])

        if pools_selected < 2:
            strength_text = "Select at least 2 pools"
            color = "#ef4444"
            pct = 0.1
        else:
            entropy = self.calculate_current_entropy()
            if entropy < 36:
                strength_text = f"Weak ({entropy:.1f} bits)"
                color = "#ef4444"
                pct = min(1.0, max(0.15, entropy / 100.0))
            elif entropy < 56:
                strength_text = f"Medium ({entropy:.1f} bits)"
                color = "#f59e0b"
                pct = min(1.0, entropy / 100.0)
            elif entropy < 75:
                strength_text = f"Strong ({entropy:.1f} bits)"
                color = "#10b981"
                pct = min(1.0, entropy / 100.0)
            else:
                strength_text = f"Very Strong ({entropy:.1f} bits)"
                color = "#6366f1"
                pct = min(1.0, entropy / 100.0)

        self.strength_lbl.configure(text=strength_text, foreground=color)

        # Clear and redraw custom canvas track
        self.strength_canvas.delete("all")
        
        w = self.strength_canvas.winfo_width()
        if w <= 0:
            # Fallback if canvas is not yet drawn/configured on grid layout initializations
            w = 340
            
        h = 8
        theme = THEMES[self.theme_var.get()]
        self.strength_canvas.configure(bg=theme["card_bg"])
        
        # Track background
        self.strength_canvas.create_rectangle(0, 0, w, h, fill=theme["border"], outline="", width=0)
        
        # Fill meter
        fill_w = w * pct
        if fill_w > 0:
            self.strength_canvas.create_rectangle(0, 0, fill_w, h, fill=color, outline="", width=0)

    def generate_password(self):
        """Generates a secure password based on GUI configuration constraints."""
        length = self.length_var.get()
        
        include_upper = self.upper_var.get()
        include_lower = self.lower_var.get()
        include_digits = self.digits_var.get()
        include_symbols = self.symbols_var.get()
        exclude_ambiguous = self.ambiguous_var.get()

        # Validations
        if length < 8 or length > 64:
            messagebox.showerror("Validation Error", "Password length must be between 8 and 64 characters.")
            return

        pools_selected = sum([include_upper, include_lower, include_digits, include_symbols])
        if pools_selected < 2:
            messagebox.showerror("Validation Error", "At least 2 character pools must be selected to generate a secure password.")
            return

        # Prepare pools
        pools = []
        lower_pool = "abcdefghijklmnopqrstuvwxyz"
        upper_pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits_pool = "0123456789"
        symbols_pool = "!@#$%^&*()_+-=[]{}|;:,.<>?/~"

        if exclude_ambiguous:
            # Exclude confusing chars: 0, o, O, 1, l, I, |
            for char in "0Oo1Il|":
                lower_pool = lower_pool.replace(char, "")
                upper_pool = upper_pool.replace(char, "")
                digits_pool = digits_pool.replace(char, "")
                symbols_pool = symbols_pool.replace(char, "")

        if include_lower:
            pools.append(lower_pool)
        if include_upper:
            pools.append(upper_pool)
        if include_digits:
            pools.append(digits_pool)
        if include_symbols:
            pools.append(symbols_pool)

        # Assemble character list
        password_chars = []
        
        # Step 1: Ensure at least one character from each selected category is included
        for pool in pools:
            password_chars.append(secrets.choice(pool))

        # Step 2: Fill out remaining characters from combined selected pools
        combined_pool = "".join(pools)
        remaining_len = length - len(password_chars)
        for _ in range(remaining_len):
            password_chars.append(secrets.choice(combined_pool))

        # Step 3: Securely shuffle using Fisher-Yates algorithm
        secure_shuffle(password_chars)
        
        password = "".join(password_chars)

        # Update output
        self.password_output_var.set(password)

        # Auto-copy to Clipboard
        try:
            pyperclip.copy(password)
            self.status_var.set("Secure password generated and copied to clipboard!")
        except Exception:
            self.status_var.set("Secure password generated! (Clipboard auto-copy failed)")

        # Log into memory history (Keep latest 5)
        self.history.insert(0, password)
        self.history_visible.insert(0, False)
        if len(self.history) > 5:
            self.history.pop()
            self.history_visible.pop()

        self.redraw_history()

    def copy_active_password(self):
        """Manually copies active display password to clipboard."""
        pw = self.password_output_var.get()
        if not pw:
            return
        try:
            pyperclip.copy(pw)
            self.status_var.set("Copied active password to clipboard.")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Failed to copy to clipboard: {e}")

    def copy_to_clipboard(self, text):
        """Copies specific text to clipboard."""
        try:
            pyperclip.copy(text)
            self.status_var.set("Copied password to clipboard.")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Failed to copy: {e}")

    def toggle_history_visibility(self, index):
        """Toggles masking state for history list item at index."""
        if 0 <= index < len(self.history_visible):
            self.history_visible[index] = not self.history_visible[index]
            self.redraw_history()

    def redraw_history(self):
        """Repopulates layout panel showing historical logs."""
        for child in self.history_inner_frame.winfo_children():
            child.destroy()

        theme = THEMES[self.theme_var.get()]

        if not self.history:
            lbl = ttk.Label(self.history_inner_frame, text="No passwords logged in this session.", 
                            font=("Segoe UI", 9, "italic"), foreground=theme["sub_fg"])
            lbl.pack(pady=20)
            return

        for idx, pw in enumerate(self.history):
            row_f = ttk.Frame(self.history_inner_frame, style="Card.TFrame", padding=6)
            row_f.pack(fill=tk.X, pady=3)

            is_visible = self.history_visible[idx]
            display_txt = pw if is_visible else "•" * len(pw)

            # Left aligned masked/unmasked text block
            pw_lbl = ttk.Label(row_f, text=display_txt, font=("Courier New", 10, "bold"), anchor=tk.W)
            pw_lbl.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

            # Quick Action Buttons (using flat standard Tk buttons styled on theme cards)
            copy_btn = tk.Button(row_f, text="📋 Copy", font=("Segoe UI", 8), bg=theme["border"], fg=theme["fg"],
                                 activebackground=theme["accent"], activeforeground="white", relief="flat", bd=0, padx=6, pady=2,
                                 command=lambda p=pw: self.copy_to_clipboard(p))
            copy_btn.pack(side=tk.RIGHT, padx=2)

            eye_txt = "🙈 Hide" if is_visible else "👁️ Show"
            eye_btn = tk.Button(row_f, text=eye_txt, font=("Segoe UI", 8), bg=theme["border"], fg=theme["fg"],
                                activebackground=theme["accent"], activeforeground="white", relief="flat", bd=0, padx=6, pady=2,
                                command=lambda index=idx: self.toggle_history_visibility(index))
            eye_btn.pack(side=tk.RIGHT, padx=2)

    def apply_theme(self):
        """Traverses UI hierarchy updating colors according to theme selection."""
        theme = THEMES[self.theme_var.get()]

        # Configure Root Widget Background
        self.root.configure(bg=theme["bg"])

        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        # Generic settings
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

        # Spinbox & Check Button styling overrides
        style.configure("TCheckbutton", background=theme["card_bg"] if "Card" in self.root.winfo_name() else theme["bg"], foreground=theme["fg"])
        style.map("TCheckbutton", background=[("active", theme["bg"])], foreground=[("active", theme["accent"])])
        
        style.configure("TRadiobutton", background=theme["bg"], foreground=theme["fg"])
        style.map("TRadiobutton", background=[("active", theme["bg"])], foreground=[("active", theme["accent"])])

        # Scale slider track color styling (basic clam override)
        style.configure("TScale", background=theme["bg"], troughcolor=theme["border"])

        # Walk widgets hierarchy
        self.recursive_theme_update(self.root, theme)
        
        # Redraw canvas meter
        self.update_strength_display()
        
        # Redraw history panels
        self.redraw_history()

    def recursive_theme_update(self, widget, theme):
        """Walks down widget hierarchy to customize underlying standard Tk element colors."""
        w_class = widget.winfo_class()
        
        try:
            if w_class == "Frame":
                widget.configure(bg=theme["bg"])
            elif w_class == "Label":
                # Check if inside a card layout for text bg adjustments
                parent_style = widget.master.winfo_class()
                widget.configure(bg=theme["bg"], fg=theme["fg"])
            elif w_class == "Canvas":
                widget.configure(bg=theme["card_bg"], highlightbackground=theme["border"])
            elif isinstance(widget, tk.Entry):
                # Standard Tk entries styling
                widget.configure(bg=theme["bg"] if widget == self.output_entry else theme["card_bg"],
                                 fg=theme["fg"], insertbackground=theme["fg"],
                                 highlightbackground=theme["border"], highlightcolor=theme["accent"])
            elif isinstance(widget, tk.Spinbox):
                # Standard Tk spinboxes styling
                widget.configure(bg=theme["card_bg"], fg=theme["fg"], buttonbackground=theme["border"],
                                 buttoncolor=theme["fg"], relief=tk.FLAT, bd=1, highlightbackground=theme["border"])
        except Exception:
            pass # Skip widget type unsupported actions
            
        for child in widget.winfo_children():
            self.recursive_theme_update(child, theme)


def main():
    root = tk.Tk()
    app = PasswordGeneratorApp(root)
    
    # Graceful intercept of window close operations
    def on_close():
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
