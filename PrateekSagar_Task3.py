#!/usr/bin/env python3
"""
AuraWeather - Advanced Real-Time Weather Application
Features:
- GUI built with tkinter (Clean, modern card-based layout)
- IP Geolocation auto-detection on startup via ipinfo.io (free tier)
- OpenWeatherMap API Integration with coordinate lookups and 5-day / 3-hour forecasts
- Pillow-based weather condition icon loader with an in-memory dictionary cache
- Dynamic weather theme: background and card colors adapt to current weather conditions
- Celsius / Fahrenheit client-side conversion toggle
- Detailed Hourly Forecast panel (next 6 hours in 3-hour intervals)
- Detailed 5-Day Daily Forecast panel (with min/max ranges and representational conditions)
- Robust inline GUI error messages for bad requests, missing inputs, and offline states
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
import io
from datetime import datetime
import math

# API Configuration
API_KEY = "8dd1754b4c4f12edb4c55738a6db041b"

# Dynamic Weather Mood Themes
WEATHER_THEMES = {
    "clear": {
        "bg": "#bae6fd",          # Light blue (sky)
        "card_bg": "#ffffff",     # Pure white card
        "fg": "#0f172a",          # Dark slate text
        "sub_fg": "#475569",      # Medium slate text
        "accent": "#eab308",      # Gold amber
        "border": "#e2e8f0",      # Light border
    },
    "clouds": {
        "bg": "#cbd5e1",          # Slate gray (overcast)
        "card_bg": "#f8fafc",     # Off-white card
        "fg": "#0f172a",          # Dark slate text
        "sub_fg": "#475569",      # Medium slate text
        "accent": "#64748b",      # Muted gray
        "border": "#e2e8f0",
    },
    "rain": {
        "bg": "#475569",          # Deep slate grey
        "card_bg": "#1e293b",     # Dark card
        "fg": "#f8fafc",          # Light text
        "sub_fg": "#94a3b8",      # Muted text
        "accent": "#38bdf8",      # Sky blue highlight
        "border": "#334155",
    },
    "snow": {
        "bg": "#f1f5f9",          # Frosty white
        "card_bg": "#ffffff",     # Clean card
        "fg": "#0f172a",          # Dark text
        "sub_fg": "#475569",
        "accent": "#0ea5e9",      # Frosty blue
        "border": "#cbd5e1",
    },
    "thunderstorm": {
        "bg": "#312e81",          # Dark purple storm
        "card_bg": "#1e293b",     # Dark card
        "fg": "#f8fafc",          # Light text
        "sub_fg": "#94a3b8",
        "accent": "#a855f7",      # Lightning purple
        "border": "#334155",
    },
    "mist": {
        "bg": "#e2e8f0",          # Foggy white
        "card_bg": "#ffffff",
        "fg": "#0f172a",
        "sub_fg": "#475569",
        "accent": "#64748b",
        "border": "#cbd5e1",
    }
}

# Dictionary to cache PIL PhotoImages in memory
icon_cache = {}


def get_weather_icon(icon_code, size=(55, 55)):
    """Downloads weather condition icons and caches them in memory."""
    cache_key = f"{icon_code}_{size[0]}"
    if cache_key in icon_cache:
        return icon_cache[cache_key]

    try:
        url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            img = img.resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            icon_cache[cache_key] = photo
            return photo
    except Exception:
        pass
    return None


class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraWeather - Premium Health & Forecast Suite")
        self.root.geometry("1000x680")
        self.root.minsize(920, 600)

        # Variables
        self.search_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="C") # C for Celsius, F for Fahrenheit
        self.error_var = tk.StringVar()
        
        # Memory caches for current weather metrics and forecasts (base stored in metric)
        self.current_data = None
        self.forecast_data = None
        
        # Draw UI Panels
        self.create_widgets()
        
        # Geolocation auto-detection on startup
        self.root.after(100, self.detect_ip_location)

    def create_widgets(self):
        """Constructs layout panels and cards."""
        # Main container grid
        self.main_frame = tk.Frame(self.root, bg="#f1f5f9", padx=15, pady=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top Header Card (Search bar + Actions + Unit Selector)
        header_card = tk.Frame(self.main_frame, bg="#ffffff", bd=1, relief="solid")
        header_card.pack(fill=tk.X, pady=(0, 15))
        
        # Inner padding for header card
        header_inner = tk.Frame(header_card, bg="#ffffff", padx=15, pady=12)
        header_inner.pack(fill=tk.X)
        
        ttk.Label(header_inner, text="📍 Search:", font=("Segoe UI", 10, "bold"), background="#ffffff").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = tk.Entry(header_inner, textvariable=self.search_var, font=("Segoe UI", 11),
                                     bg="#f8fafc", fg="#0f172a", insertbackground="#0f172a",
                                     relief=tk.FLAT, highlightthickness=1, highlightbackground="#cbd5e1",
                                     highlightcolor="#4f46e5", width=25)
        self.search_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        self.search_entry.bind("<Return>", lambda e: self.fetch_weather_action())

        # Search button
        self.search_btn = tk.Button(header_inner, text="Get Weather", font=("Segoe UI", 9, "bold"),
                                    bg="#4f46e5", fg="white", activebackground="#4338ca", activeforeground="white",
                                    relief="flat", bd=0, padx=12, pady=5, command=self.fetch_weather_action)
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Auto-Locate button
        self.locate_btn = tk.Button(header_inner, text="📍 Auto-Locate", font=("Segoe UI", 9),
                                    bg="#e2e8f0", fg="#0f172a", activebackground="#cbd5e1", activeforeground="#0f172a",
                                    relief="flat", bd=0, padx=10, pady=5, command=self.detect_ip_location)
        self.locate_btn.pack(side=tk.LEFT, padx=5)

        # Unit Toggle Frame
        unit_frame = tk.Frame(header_inner, bg="#ffffff")
        unit_frame.pack(side=tk.RIGHT, padx=5)
        
        self.c_btn = ttk.Radiobutton(unit_frame, text="°C", variable=self.unit_var, value="C", command=self.toggle_temperature_units)
        self.c_btn.pack(side=tk.LEFT, padx=3)
        self.f_btn = ttk.Radiobutton(unit_frame, text="°F", variable=self.unit_var, value="F", command=self.toggle_temperature_units)
        self.f_btn.pack(side=tk.LEFT, padx=3)

        # Error notification label inside header
        self.error_lbl = tk.Label(header_inner, textvariable=self.error_var, fg="#ef4444", bg="#ffffff",
                                  font=("Segoe UI", 9, "bold"), anchor=tk.W)
        self.error_lbl.pack(side=tk.LEFT, padx=15)

        # Workspace split (Left: Current summary card, Right: Forecasts lists)
        workspace = tk.Frame(self.main_frame, bg="#f1f5f9")
        workspace.pack(fill=tk.BOTH, expand=True)

        workspace.columnconfigure(0, weight=0, minsize=420)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        # LEFT SIDE COLUMN
        self.left_col = tk.Frame(workspace, bg="#f1f5f9")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Main Current Weather Card
        self.current_card = tk.Frame(self.left_col, bg="#ffffff", bd=1, relief="solid", padx=20, pady=20)
        self.current_card.pack(fill=tk.BOTH, expand=True)

        # Location details
        self.location_lbl = tk.Label(self.current_card, text="Select Location", font=("Segoe UI", 18, "bold"), bg="#ffffff", fg="#0f172a")
        self.location_lbl.pack(anchor=tk.W, pady=(0, 2))
        
        self.date_lbl = tk.Label(self.current_card, text="--:--", font=("Segoe UI", 9), bg="#ffffff", fg="#64748b")
        self.date_lbl.pack(anchor=tk.W, pady=(0, 15))

        # Large Temperature and icon row
        temp_row = tk.Frame(self.current_card, bg="#ffffff")
        temp_row.pack(fill=tk.X, pady=10)
        
        self.main_icon_lbl = tk.Label(temp_row, bg="#ffffff")
        self.main_icon_lbl.pack(side=tk.LEFT, padx=(0, 10))
        
        self.temp_lbl = tk.Label(temp_row, text="--°", font=("Segoe UI", 48, "bold"), bg="#ffffff", fg="#0f172a")
        self.temp_lbl.pack(side=tk.LEFT)

        self.condition_lbl = tk.Label(self.current_card, text="--", font=("Segoe UI", 14, "bold"), bg="#ffffff", fg="#0f172a")
        self.condition_lbl.pack(anchor=tk.W, pady=(5, 15))

        # Horizontal separator
        sep = ttk.Separator(self.current_card, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=10)

        # Extra Weather Metrics Grid (2x2)
        metrics_frame = tk.Frame(self.current_card, bg="#ffffff")
        metrics_frame.pack(fill=tk.X, pady=10)

        metrics_frame.columnconfigure(0, weight=1)
        metrics_frame.columnconfigure(1, weight=1)

        # Metric 1: Humidity
        self.humidity_card = tk.Frame(metrics_frame, bg="#f8fafc", padx=10, pady=8, bd=1, relief="solid")
        self.humidity_card.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        tk.Label(self.humidity_card, text="Humidity", font=("Segoe UI", 8), bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
        self.humidity_val = tk.Label(self.humidity_card, text="--", font=("Segoe UI", 12, "bold"), bg="#f8fafc", fg="#0f172a")
        self.humidity_val.pack(anchor=tk.W)

        # Metric 2: Wind
        self.wind_card = tk.Frame(metrics_frame, bg="#f8fafc", padx=10, pady=8, bd=1, relief="solid")
        self.wind_card.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        tk.Label(self.wind_card, text="Wind Speed", font=("Segoe UI", 8), bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
        self.wind_val = tk.Label(self.wind_card, text="--", font=("Segoe UI", 12, "bold"), bg="#f8fafc", fg="#0f172a")
        self.wind_val.pack(anchor=tk.W)

        # Metric 3: Pressure
        self.pressure_card = tk.Frame(metrics_frame, bg="#f8fafc", padx=10, pady=8, bd=1, relief="solid")
        self.pressure_card.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky="ew")
        tk.Label(self.pressure_card, text="Pressure", font=("Segoe UI", 8), bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
        self.pressure_val = tk.Label(self.pressure_card, text="--", font=("Segoe UI", 12, "bold"), bg="#f8fafc", fg="#0f172a")
        self.pressure_val.pack(anchor=tk.W)

        # Metric 4: Visibility
        self.visibility_card = tk.Frame(metrics_frame, bg="#f8fafc", padx=10, pady=8, bd=1, relief="solid")
        self.visibility_card.grid(row=1, column=1, padx=(5, 0), pady=(5, 0), sticky="ew")
        tk.Label(self.visibility_card, text="Visibility", font=("Segoe UI", 8), bg="#f8fafc", fg="#64748b").pack(anchor=tk.W)
        self.visibility_val = tk.Label(self.visibility_card, text="--", font=("Segoe UI", 12, "bold"), bg="#f8fafc", fg="#0f172a")
        self.visibility_val.pack(anchor=tk.W)


        # RIGHT SIDE COLUMN
        self.right_col = tk.Frame(workspace, bg="#f1f5f9")
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 1. Hourly Forecast Card
        self.hourly_card = tk.Frame(self.right_col, bg="#ffffff", bd=1, relief="solid", padx=15, pady=15)
        self.hourly_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(self.hourly_card, text="HOURLY FORECAST (NEXT 6 HOURS)", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor=tk.W, pady=(0, 10))

        self.hourly_row = tk.Frame(self.hourly_card, bg="#ffffff")
        self.hourly_row.pack(fill=tk.X)

        # 2. Daily Forecast Card
        self.daily_card = tk.Frame(self.right_col, bg="#ffffff", bd=1, relief="solid", padx=15, pady=15)
        self.daily_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.daily_card, text="5-DAY DAILY FORECAST", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#0f172a").pack(anchor=tk.W, pady=(0, 10))

        self.daily_list_frame = tk.Frame(self.daily_card, bg="#ffffff")
        self.daily_list_frame.pack(fill=tk.BOTH, expand=True)

    def detect_ip_location(self):
        """Startup hook that detects user's location via IP Geolocation APIs."""
        self.error_var.set("")
        self.status_bar_update("Detecting location via IP...")
        try:
            r = requests.get("https://ipinfo.io/json", timeout=3.5)
            if r.status_code == 200:
                data = r.json()
                city = data.get("city")
                if city:
                    self.search_var.set(city)
                    self.fetch_weather(city)
                    return
        except Exception:
            pass
            
        # Offline fallback default
        self.search_var.set("New Delhi")
        self.fetch_weather("New Delhi")

    def fetch_weather_action(self):
        """Search action wrapper handling entry inputs."""
        city = self.search_var.get().strip()
        if not city:
            self.error_var.set("Please enter a city name.")
            return
        self.error_var.set("")
        self.fetch_weather(city)

    def fetch_weather(self, city):
        """Downloads weather and forecast data from OpenWeatherMap."""
        self.status_bar_update(f"Searching for '{city}'...")
        try:
            # Step 1: Geocoding Lookup API
            geo_url = "https://api.openweathermap.org/geo/1.0/direct"
            geo_params = {"q": city, "limit": 1, "appid": API_KEY}
            geo_res = requests.get(geo_url, params=geo_params, timeout=4)
            
            if geo_res.status_code != 200:
                self.error_var.set("Weather API request error.")
                return
                
            geo_data = geo_res.json()
            if not geo_data:
                self.error_var.set(f"City '{city}' not found.")
                return
                
            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]
            name = geo_data[0]["name"]
            country = geo_data[0].get("country", "")

            # Step 2: Current Weather metrics API
            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            weather_params = {"lat": lat, "lon": lon, "units": "metric", "appid": API_KEY}
            w_res = requests.get(weather_url, params=weather_params, timeout=4)
            
            if w_res.status_code != 200:
                self.error_var.set("Failed to fetch weather metrics.")
                return
            self.current_data = w_res.json()
            self.current_data["display_name"] = f"{name}, {country}"

            # Step 3: Forecast metrics API (5 Days / 3 Hours steps)
            forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
            f_res = requests.get(forecast_url, params=weather_params, timeout=4)
            
            if f_res.status_code != 200:
                self.error_var.set("Failed to fetch forecast details.")
                return
            self.forecast_data = f_res.json()

            # Refresh display panels
            self.update_weather_display()
            self.error_var.set("") # Clear any prior warnings
            self.status_bar_update("Ready")
            
        except requests.exceptions.Timeout:
            self.error_var.set("Network timeout. Please check connections.")
        except requests.exceptions.ConnectionError:
            self.error_var.set("Network offline. Connection refused.")
        except Exception as e:
            self.error_var.set(f"Unexpected error: {e}")

    def update_weather_display(self):
        """Fills up UI frames with data and applies weather condition themes."""
        if not self.current_data or not self.forecast_data:
            return

        # 1. Resolve Weather Condition Theme mapping
        condition_id = self.current_data["weather"][0]["id"]
        main_cond = self.current_data["weather"][0]["main"].lower()
        
        # Map OpenWeather ID groups
        theme_key = "clouds"
        if 200 <= condition_id < 300:
            theme_key = "thunderstorm"
        elif 300 <= condition_id < 600:
            theme_key = "rain"
        elif 600 <= condition_id < 700:
            theme_key = "snow"
        elif condition_id == 800:
            theme_key = "clear"
        elif 701 <= condition_id < 800:
            theme_key = "mist"
            
        self.apply_theme_palette(theme_key)

        # 2. Render Main Card Text details
        name = self.current_data["display_name"]
        self.location_lbl.configure(text=name)
        
        query_time = datetime.fromtimestamp(self.current_data["dt"]).strftime("%A, %b %d, %H:%M")
        self.date_lbl.configure(text=f"Last updated: {query_time}")
        
        cond_desc = self.current_data["weather"][0]["description"].title()
        self.condition_lbl.configure(text=cond_desc)

        # Get icon PhotoImage via PIL
        icon_code = self.current_data["weather"][0]["icon"]
        p_img = get_weather_icon(icon_code, size=(85, 85))
        if p_img:
            self.main_icon_lbl.configure(image=p_img)
            self.main_icon_lbl.image = p_img # keep reference

        # 3. Dynamic Values rendering (responds to Celsius/Fahrenheit toggle)
        self.refresh_metric_labels()
        
        # 4. Hourly Forecast Grid rendering
        self.render_hourly_panel()
        
        # 5. 5-Day Forecast Grid rendering
        self.render_daily_panel()

    def refresh_metric_labels(self):
        """Converts values client-side depending on unit variables and updates UI labels."""
        if not self.current_data:
            return

        # Temperature
        temp_c = self.current_data["main"]["temp"]
        if self.unit_var.get() == "C":
            self.temp_lbl.configure(text=f"{round(temp_c)}°")
        else:
            temp_f = temp_c * 9/5 + 32
            self.temp_lbl.configure(text=f"{round(temp_f)}°")

        # Humidity
        humidity = self.current_data["main"]["humidity"]
        self.humidity_val.configure(text=f"{humidity}%")

        # Wind Speed
        wind_c = self.current_data["wind"]["speed"] # m/s
        if self.unit_var.get() == "C":
            self.wind_val.configure(text=f"{wind_c:.1f} m/s")
        else:
            wind_f = wind_c * 2.23694 # mph
            self.wind_val.configure(text=f"{wind_f:.1f} mph")

        # Pressure
        pressure = self.current_data["main"]["pressure"]
        self.pressure_val.configure(text=f"{pressure} hPa")

        # Visibility
        visibility_m = self.current_data.get("visibility", 10000)
        visibility_km = visibility_m / 1000.0
        if self.unit_var.get() == "C":
            self.visibility_val.configure(text=f"{visibility_km:.1f} km")
        else:
            visibility_mi = visibility_km * 0.621371
            self.visibility_val.configure(text=f"{visibility_mi:.1f} mi")

    def render_hourly_panel(self):
        """Loads forecast intervals for the next 6 hours in horizontal widgets."""
        for child in self.hourly_row.winfo_children():
            child.destroy()

        if not self.forecast_data:
            return

        # We display indices [0, 1] corresponding to next 3 and 6 hours
        forecast_list = self.forecast_data.get("list", [])
        theme = WEATHER_THEMES[self.theme_key]
        
        # Include current weather index as the start comparison
        current_time_str = "Now"
        current_temp = self.current_data["main"]["temp"]
        current_icon = self.current_data["weather"][0]["icon"]
        current_short = self.current_data["weather"][0]["main"]
        
        indices_list = [(current_time_str, current_temp, current_icon, current_short)]
        
        # Add next two hourly forecast indices
        for i in range(min(2, len(forecast_list))):
            item = forecast_list[i]
            dt = datetime.fromtimestamp(item["dt"])
            time_str = dt.strftime("%H:%M")
            temp = item["main"]["temp"]
            icon = item["weather"][0]["icon"]
            short_desc = item["weather"][0]["main"]
            indices_list.append((time_str, temp, icon, short_desc))

        self.hourly_row.columnconfigure((0, 1, 2), weight=1)

        for col_idx, (t_str, temp_c, icon_code, s_desc) in enumerate(indices_list):
            cell = tk.Frame(self.hourly_row, bg=theme["card_bg"], bd=1, relief="solid", padx=10, pady=10)
            cell.grid(row=0, column=col_idx, padx=5, sticky="ew")

            # Time header
            tk.Label(cell, text=t_str, font=("Segoe UI", 9, "bold"), bg=theme["card_bg"], fg=theme["fg"]).pack()
            
            # Icon
            cell_icon = tk.Label(cell, bg=theme["card_bg"])
            cell_icon.pack(pady=2)
            p_img = get_weather_icon(icon_code, size=(45, 45))
            if p_img:
                cell_icon.configure(image=p_img)
                cell_icon.image = p_img # reference

            # Temp
            if self.unit_var.get() == "C":
                temp_text = f"{round(temp_c)}°C"
            else:
                temp_text = f"{round(temp_c * 9/5 + 32)}°F"
                
            tk.Label(cell, text=temp_text, font=("Segoe UI", 11, "bold"), bg=theme["card_bg"], fg=theme["fg"]).pack()
            
            # Short condition text
            tk.Label(cell, text=s_desc, font=("Segoe UI", 8), bg=theme["card_bg"], fg=theme["sub_fg"]).pack()

    def render_daily_panel(self):
        """Aggregates and renders 5-day daily forecast metrics vertically."""
        for child in self.daily_list_frame.winfo_children():
            child.destroy()

        if not self.forecast_data:
            return

        forecast_list = self.forecast_data.get("list", [])
        
        # Group list items by date
        from collections import defaultdict
        daily_groups = defaultdict(list)
        for item in forecast_list:
            dt_txt = item.get("dt_txt", "")
            date_key = dt_txt.split(" ")[0]
            daily_groups[date_key].append(item)

        # Exclude today's entries to render future 5 days cleanly
        today_key = datetime.now().strftime("%Y-%m-%d")
        
        daily_forecast_days = []
        for date_str, items in sorted(daily_groups.items()):
            if date_str == today_key:
                continue
            if len(daily_forecast_days) >= 5:
                break
                
            min_temp = min(x["main"]["temp"] for x in items)
            max_temp = max(x["main"]["temp"] for x in items)
            
            # Select mid-day slot for weather icon
            rep_item = items[0]
            for x in items:
                if "12:00:00" in x.get("dt_txt", ""):
                    rep_item = x
                    break
                elif "15:00:00" in x.get("dt_txt", ""):
                    rep_item = x

            daily_forecast_days.append({
                "date": date_str,
                "min_temp": min_temp,
                "max_temp": max_temp,
                "desc": rep_item["weather"][0]["main"],
                "icon": rep_item["weather"][0]["icon"]
            })

        theme = WEATHER_THEMES[self.theme_key]

        for row_idx, day_data in enumerate(daily_forecast_days):
            row_frame = tk.Frame(self.daily_list_frame, bg=theme["card_bg"], bd=1, relief="solid", padx=12, pady=6)
            row_frame.pack(fill=tk.X, pady=3)

            # Date calculation (Day name)
            dt = datetime.strptime(day_data["date"], "%Y-%m-%d")
            day_name = dt.strftime("%A")
            short_date = dt.strftime("%b %d")

            # Day title
            tk.Label(row_frame, text=f"{day_name} ({short_date})", font=("Segoe UI", 9, "bold"),
                     bg=theme["card_bg"], fg=theme["fg"], width=18, anchor=tk.W).pack(side=tk.LEFT)

            # Weather Icon
            day_icon_lbl = tk.Label(row_frame, bg=theme["card_bg"])
            day_icon_lbl.pack(side=tk.LEFT, padx=10)
            p_img = get_weather_icon(day_data["icon"], size=(40, 40))
            if p_img:
                day_icon_lbl.configure(image=p_img)
                day_icon_lbl.image = p_img

            # Muted condition label
            tk.Label(row_frame, text=day_data["desc"], font=("Segoe UI", 9),
                     bg=theme["card_bg"], fg=theme["sub_fg"], width=12, anchor=tk.W).pack(side=tk.LEFT, padx=10)

            # Temp Min - Max
            min_c = day_data["min_temp"]
            max_c = day_data["max_temp"]
            
            if self.unit_var.get() == "C":
                temp_range_text = f"Min: {round(min_c)}°C  /  Max: {round(max_c)}°C"
            else:
                min_f = min_c * 9/5 + 32
                max_f = max_c * 9/5 + 32
                temp_range_text = f"Min: {round(min_f)}°F  /  Max: {round(max_f)}°F"

            tk.Label(row_frame, text=temp_range_text, font=("Segoe UI", 9, "bold"),
                     bg=theme["card_bg"], fg=theme["fg"]).pack(side=tk.RIGHT)

    def toggle_temperature_units(self):
        """Switches all displayed temperatures client-side instantly."""
        self.refresh_metric_labels()
        self.render_hourly_panel()
        self.render_daily_panel()
        self.status_bar_update(f"Units toggled to °{self.unit_var.get()}")

    def apply_theme_palette(self, theme_key):
        """Recursively styles Tkinter widgets depending on weather conditions."""
        self.theme_key = theme_key
        theme = WEATHER_THEMES[theme_key]

        # Background main body color updates
        self.main_frame.configure(bg=theme["bg"])
        self.left_col.configure(bg=theme["bg"])
        self.right_col.configure(bg=theme["bg"])

        # Styled ttk radio buttons
        style = ttk.Style()
        style.configure("TRadiobutton", background="#ffffff", foreground="#0f172a")

        # Traverse standard sub-widgets
        self.recursive_style_update(self.root, theme)

    def recursive_style_update(self, widget, theme):
        """Walks down widget hierarchy adjusting standard colors to match active themes."""
        w_class = widget.winfo_class()
        
        try:
            # Custom styled cards
            if widget in [self.current_card, self.hourly_card, self.daily_card, self.daily_list_frame, self.hourly_row]:
                widget.configure(bg=theme["card_bg"], highlightbackground=theme["border"])
            elif widget in [self.humidity_card, self.wind_card, self.pressure_card, self.visibility_card]:
                widget.configure(bg=theme["card_bg"], highlightbackground=theme["border"])
            elif w_class == "Label":
                # Determine bg color based on parent hierarchy
                parent = widget.master
                if parent in [self.humidity_card, self.wind_card, self.pressure_card, self.visibility_card, self.current_card, self.hourly_card, self.daily_card, self.daily_list_frame, self.hourly_row]:
                    widget.configure(bg=theme["card_bg"], fg=theme["fg"])
                else:
                    # Let default labels outside cards remain background transparent
                    pass
            elif w_class == "Frame":
                # Let generic frames inside main container use current theme backgrounds
                if widget not in [self.main_frame, self.left_col, self.right_col]:
                    widget.configure(bg=theme["card_bg"])
        except Exception:
            pass
            
        for child in widget.winfo_children():
            self.recursive_style_update(child, theme)

    def status_bar_update(self, text):
        """Modifies status message directly on root frame title/status variables."""
        # Setup self.status_lbl if not configured, or modify title
        self.root.title(f"AuraWeather - {text}")


def main():
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
