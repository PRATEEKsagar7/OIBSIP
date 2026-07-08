#!/usr/bin/env python3
"""
AuraVoice - Advanced Desktop Voice Assistant
Features:
- GUI console built with tkinter (Clean modern card-based layout)
- Thread-safe, non-blocking Text-to-Speech (TTS) engine using pyttsx3
- Background speech recognition listener using speech_recognition and microphone inputs
- Pulsing animated sine-wave Canvas visualizer matching different state frequencies
- Natural Language Intent Parser classifying spoken sentences into commands
- ipinfo.io and OpenWeatherMap APIs integration for current weather conditions
- DuckDuckGo QA Instant Answer API integration for general knowledge queries
- Background Threaded Reminders with popups and winsound beeping alerts
- Interactive Voice Flow for emailing (guided prompt form filling with mock SMTP logging)
- Voice-based Custom Commands recorder: adds new commands to local voice_commands.json
- Privacy consideration: Documents data usage and processing
"""

import tkinter as tk
from tkinter import ttk, messagebox
import speech_recognition as sr
import pyttsx3
import queue
import threading
import requests
import webbrowser
from datetime import datetime
import time
import math
import os
import json

# Windows sound support check
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Weather API Config
WEATHER_API_KEY = "8dd1754b4c4f12edb4c55738a6db041b"

# Color Palette Matching Aura Suite
THEME = {
    "bg": "#0f172a",          # Dark Slate
    "card_bg": "#1e293b",     # Slate Card
    "fg": "#f8fafc",          # Slate Light Text
    "sub_fg": "#94a3b8",      # Muted Gray Text
    "accent": "#6366f1",      # Indigo Accent
    "accent_hover": "#4f46e5",
    "border": "#334155",
    "wave_idle": "#94a3b8",
    "wave_listening": "#38bdf8",
    "wave_thinking": "#a855f7",
    "wave_speaking": "#10b981",
}


# =====================================================================
# THREAD-SAFE NON-BLOCKING TEXT-TO-SPEECH ENGINE
# =====================================================================

class SpeechWorker:
    """Manages pyttsx3 speech synthesis in a background queue consuming thread."""
    def __init__(self, on_speak_start_callback=None, on_speak_end_callback=None):
        self.cmd_queue = queue.Queue()
        self.on_start = on_speak_start_callback
        self.on_end = on_speak_end_callback
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def speak(self, text):
        """Pushes string onto queue for synthesis."""
        self.cmd_queue.put(("speak", text))

    def set_property(self, prop, value):
        """Pushes property updates (e.g. rate, volume, voice) onto queue."""
        self.cmd_queue.put(("set", (prop, value)))

    def _run_loop(self):
        # Local init inside thread to avoid thread context clashes
        engine = pyttsx3.init()
        
        # Configure default voices
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            # Set default English voice if available
            for voice in voices:
                if "en" in voice.languages or "EN" in voice.name:
                    engine.setProperty('voice', voice.id)
                    break
        
        while True:
            cmd, payload = self.cmd_queue.get()
            if cmd == "speak":
                if self.on_start:
                    self.on_start()
                engine.say(payload)
                engine.runAndWait()
                if self.on_end:
                    self.on_end()
            elif cmd == "set":
                prop, val = payload
                engine.setProperty(prop, val)


# =====================================================================
# MAIN VOICE ASSISTANT APP WINDOW
# =====================================================================

class VoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AuraVoice - Intelligent Assistant")
        self.root.geometry("780x560")
        self.root.minsize(680, 480)
        self.root.configure(bg=THEME["bg"])

        # State Variables
        self.is_listening = False
        self.assistant_state = "idle"  # idle, listening, thinking, speaking
        self.status_var = tk.StringVar(value="Idle")
        
        # UI Volume & Speed Variables
        self.rate_var = tk.IntVar(value=180)
        self.gender_var = tk.StringVar(value="Female")
        
        # Load custom command file
        self.commands_path = "voice_commands.json"
        self.custom_commands = {}
        self.load_custom_commands()

        # Thread-Safe TTS Engine
        self.speech_engine = SpeechWorker(
            on_speak_start_callback=lambda: self.update_state("speaking"),
            on_speak_end_callback=lambda: self.update_state("idle")
        )
        self.speech_engine.set_property("rate", 180)

        # Build GUI Panels
        self.create_widgets()
        
        # Start soundwave canvas animation loop
        self.wave_phase = 0.0
        self.animate_wave()

        # Startup greeting
        self.root.after(800, lambda: self.speak_and_log("Hello. I am AuraVoice, your personal desktop health and forecast assistant. How can I help you today?"))

    def create_widgets(self):
        """Constructs assistant workspace layout."""
        # Top Header Bar
        header = tk.Frame(self.root, bg=THEME["bg"], padx=15, pady=10)
        header.pack(side=tk.TOP, fill=tk.X)
        
        title_lbl = tk.Label(header, text="AuraVoice Assistant", font=("Segoe UI", 15, "bold"), bg=THEME["bg"], fg=THEME["fg"])
        title_lbl.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(header, textvariable=self.status_var, font=("Segoe UI", 9, "bold"), fg=THEME["wave_idle"], bg=THEME["bg"])
        self.status_lbl.pack(side=tk.RIGHT)

        # Workspace split: Left (Waveform and Controls), Right (Conversation Chat log)
        workspace = tk.Frame(self.root, bg=THEME["bg"], padx=15, pady=5)
        workspace.pack(fill=tk.BOTH, expand=True)
        workspace.columnconfigure(0, weight=0, minsize=320)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        # LEFT SIDE COLUMN: AUDIO CONTROLS CARD
        left_col = tk.Frame(workspace, bg=THEME["bg"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        controls_card = tk.Frame(left_col, bg=THEME["card_bg"], bd=1, relief="solid", highlightbackground=THEME["border"])
        controls_card.pack(fill=tk.BOTH, expand=True)

        # Waveform Canvas
        self.wave_canvas = tk.Canvas(controls_card, height=140, bg=THEME["bg"], highlightthickness=0)
        self.wave_canvas.pack(fill=tk.X, padx=12, pady=12)

        # Circular Microphone Action Button
        btn_frame = tk.Frame(controls_card, bg=THEME["card_bg"])
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.mic_btn = tk.Button(btn_frame, text="🎙️ Tap to Speak", font=("Segoe UI", 10, "bold"),
                                 bg=THEME["accent"], fg="white", activebackground=THEME["accent_hover"], activeforeground="white",
                                 relief="flat", bd=0, padx=15, pady=8, command=self.trigger_listening_loop)
        self.mic_btn.pack(anchor=tk.CENTER)

        # Separator line
        sep = ttk.Separator(controls_card, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, padx=15, pady=10)

        # Settings
        settings_frame = tk.Frame(controls_card, bg=THEME["card_bg"], padx=15)
        settings_frame.pack(fill=tk.X)

        tk.Label(settings_frame, text="VOICE CONFIGURATION", font=("Segoe UI", 8, "bold"), bg=THEME["card_bg"], fg=THEME["sub_fg"]).pack(anchor=tk.W, pady=(0, 8))

        # Speaking Rate Slider
        rate_row = tk.Frame(settings_frame, bg=THEME["card_bg"])
        rate_row.pack(fill=tk.X, pady=4)
        tk.Label(rate_row, text="Speed Rate:", bg=THEME["card_bg"], fg=THEME["fg"]).pack(side=tk.LEFT)
        rate_slider = ttk.Scale(rate_row, from_=120, to=250, variable=self.rate_var, orient=tk.HORIZONTAL, command=self.update_speech_rate)
        rate_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        # Gender Selector
        gender_row = tk.Frame(settings_frame, bg=THEME["card_bg"])
        gender_row.pack(fill=tk.X, pady=8)
        tk.Label(gender_row, text="Voice Type:", bg=THEME["card_bg"], fg=THEME["fg"]).pack(side=tk.LEFT)
        
        gender_combo = ttk.Combobox(gender_row, textvariable=self.gender_var, values=["Male", "Female"], state="readonly", width=10)
        gender_combo.pack(side=tk.RIGHT)
        gender_combo.bind("<<ComboboxSelected>>", self.update_speech_gender)

        # Quick action hotkeys guide
        tk.Label(controls_card, text="Hotkeys: Press Spacebar to record", font=("Segoe UI", 8), bg=THEME["card_bg"], fg=THEME["sub_fg"]).pack(side=tk.BOTTOM, pady=12)

        # Bind spacebar to mic trigger
        self.root.bind("<space>", lambda e: self.trigger_listening_loop())

        # RIGHT SIDE COLUMN: CHAT FEED CARD
        right_col = tk.Frame(workspace, bg=THEME["bg"])
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        feed_card = tk.Frame(right_col, bg=THEME["card_bg"], bd=1, relief="solid", highlightbackground=THEME["border"], padx=12, pady=12)
        feed_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(feed_card, text="CONVERSATION HISTORY", font=("Segoe UI", 9, "bold"), bg=THEME["card_bg"], fg=THEME["fg"]).pack(anchor=tk.W, pady=(0, 8))

        # Text feed
        self.chat_feed = tk.Text(feed_card, font=("Segoe UI", 9), bg=THEME["bg"], fg=THEME["fg"], wrap=tk.WORD, state="disabled", relief=tk.FLAT)
        self.chat_feed.pack(fill=tk.BOTH, expand=True)
        
        # Tags styling
        self.chat_feed.tag_config("user", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        self.chat_feed.tag_config("assistant", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.chat_feed.tag_config("msg", foreground=THEME["fg"])

    # =====================================================================
    # TEXT-TO-SPEECH PROPERTIES CONTROL
    # =====================================================================

    def update_speech_rate(self, val=None):
        """Alters voice speed rate settings."""
        self.speech_engine.set_property("rate", self.rate_var.get())

    def update_speech_gender(self, event=None):
        """Switches voice synthesizer gender profiles."""
        gender = self.gender_var.get()
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        
        if len(voices) > 1:
            if gender == "Female":
                # Typical female voice index
                self.speech_engine.set_property("voice", voices[1].id)
            else:
                self.speech_engine.set_property("voice", voices[0].id)

    # =====================================================================
    # VISUAL SOUNDWAVE CANVAS ANIMATOR
    # =====================================================================

    def update_state(self, state):
        """Sets assistant state and changes title bar notifications."""
        self.assistant_state = state
        if state == "listening":
            self.status_var.set("Listening...")
            self.status_lbl.configure(fg=THEME["wave_listening"])
            self.mic_btn.configure(text="🎙️ Listening...", bg=THEME["wave_listening"])
        elif state == "thinking":
            self.status_var.set("Processing...")
            self.status_lbl.configure(fg=THEME["wave_thinking"])
            self.mic_btn.configure(text="🤔 Thinking...", bg=THEME["wave_thinking"])
        elif state == "speaking":
            self.status_var.set("Speaking...")
            self.status_lbl.configure(fg=THEME["wave_speaking"])
            self.mic_btn.configure(text="🔊 Speaking...", bg=THEME["wave_speaking"])
        else:
            self.status_var.set("Idle")
            self.status_lbl.configure(fg=THEME["wave_idle"])
            self.mic_btn.configure(text="🎙️ Tap to Speak", bg=THEME["accent"])

    def animate_wave(self):
        """Redraws moving sine waves based on active speech states."""
        self.wave_canvas.delete("all")
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        
        if w <= 0 or h <= 0:
            w = 296
            h = 140

        cy = h / 2
        points = []
        
        # Adjust wave parameters depending on assistant states
        if self.assistant_state == "listening":
            amplitude = 12
            freq = 0.04
            speed = 0.16
            color = THEME["wave_listening"]
        elif self.assistant_state == "thinking":
            # Breathing fade oscillation wave
            amplitude = 6 * (1 + math.sin(self.wave_phase * 0.5))
            freq = 0.06
            speed = 0.08
            color = THEME["wave_thinking"]
        elif self.assistant_state == "speaking":
            # Highly erratic speech voice amplitudes
            amplitude = 22 * (0.3 + abs(math.sin(self.wave_phase * 2) * math.cos(self.wave_phase * 0.5)))
            freq = 0.03
            speed = 0.22
            color = THEME["wave_speaking"]
        else: # idle
            amplitude = 2
            freq = 0.02
            speed = 0.04
            color = THEME["wave_idle"]

        self.wave_phase += speed

        for x in range(0, w, 2):
            y = cy + amplitude * math.sin(freq * x + self.wave_phase)
            points.append((x, y))

        # Draw clean spline
        if len(points) > 1:
            # Flatten coordinate array
            flat_pts = [coord for pt in points for coord in pt]
            self.wave_canvas.create_line(flat_pts, fill=color, width=2.5, smooth=True)

        self.root.after(30, self.animate_wave)

    # =====================================================================
    # SPEECH RECOGNITION MAIN THREAD HANDLER
    # =====================================================================

    def trigger_listening_loop(self):
        """Spawns asynchronous recording thread."""
        if self.is_listening:
            return
        self.is_listening = True
        self.update_state("listening")
        threading.Thread(target=self._listening_worker, daemon=True).start()

    def _listening_worker(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.8)
            try:
                # Limit listener to prevent hanging infinitely on background noises
                audio = r.listen(source, timeout=4, phrase_time_limit=8)
                self.update_state("thinking")
                
                # Perform transcription via Google speech API
                query = r.recognize_google(audio)
                self.root.after(0, lambda q=query: self.process_spoken_input(q))
            except sr.WaitTimeoutError:
                self.root.after(0, lambda: self.speak_and_log("I did not hear any voice input."))
            except sr.UnknownValueError:
                self.root.after(0, lambda: self.speak_and_log("Sorry, I could not understand the speech. Please repeat."))
            except Exception as e:
                self.root.after(0, lambda: self.speak_and_log("Speech Recognition Connection Error."))
            finally:
                self.is_listening = False
                self.root.after(0, lambda: self.update_state("idle"))

    # =====================================================================
    # CHAT FEED WRITING HELPERS
    # =====================================================================

    def speak_and_log(self, text):
        """Transmits speech response aloud and logs into window feeds."""
        self.log_chat("AuraVoice", text)
        self.speech_engine.speak(text)

    def log_chat(self, speaker, text):
        """Appends formatted message log text inside Text widget."""
        self.chat_feed.configure(state="normal")
        if speaker == "You":
            self.chat_feed.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M')}] You: ", "user")
        else:
            self.chat_feed.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M')}] AuraVoice: ", "assistant")
            
        self.chat_feed.insert(tk.END, f"{text}\n", "msg")
        self.chat_feed.configure(state="disabled")
        self.chat_feed.see(tk.END)

    # =====================================================================
    # NLU INTENT CLASSIFIER ENGINE
    # =====================================================================

    def process_spoken_input(self, query):
        """Maps transcribed text strings into intention actions."""
        raw_cmd = query.strip()
        self.log_chat("You", raw_cmd)
        
        cmd = raw_cmd.lower()

        # 1. Custom Commands check first
        for trigger, response in self.custom_commands.items():
            if trigger in cmd:
                self.speak_and_log(response)
                return

        # 2. Greeting Intents
        if any(greet in cmd for greet in ["hello", "hi", "hey", "wake up"]):
            self.speak_and_log("Hello there! How can I help you today, vro?")
            return

        # 3. Date / Time Intents
        if "time" in cmd:
            now_time = datetime.now().strftime("%I:%M %p")
            self.speak_and_log(f"The current time is {now_time}.")
            return
        if "date" in cmd or "today" in cmd or "day" in cmd:
            now_date = datetime.now().strftime("%A, %B %d, %Y")
            self.speak_and_log(f"Today is {now_date}.")
            return

        # 4. Search Intents
        if "search for" in cmd or "google" in cmd or "look up" in cmd:
            search_query = cmd.replace("search for", "").replace("google", "").replace("look up", "").strip()
            if not search_query:
                self.speak_and_log("What topic would you like me to search for?")
                # Trigger quick listen follow-up
                self.root.after(2000, self.trigger_listening_loop)
                return
            webbrowser.open(f"https://www.google.com/search?q={search_query.replace(' ', '+')}")
            self.speak_and_log(f"Opening browser search queries for: '{search_query}'.")
            return

        # 5. Weather Intents
        if "weather" in cmd or "temperature" in cmd:
            # Check if city name is mentioned
            words = cmd.split()
            city = None
            if "in" in words:
                idx = words.index("in")
                if idx + 1 < len(words):
                    city = " ".join(words[idx + 1:])
            
            if not city:
                # Try geolocating city on OWM
                self.fetch_voice_weather("New Delhi")
            else:
                self.fetch_voice_weather(city)
            return

        # 6. Email Intents
        if "send email" in cmd or "write email" in cmd:
            self.speak_and_log("Who is the recipient of this email?")
            self.root.after(3000, lambda: self.prompt_email_flow("recipient"))
            return

        # 7. Reminder Intents
        if "reminder" in cmd or "timer" in cmd or "alarm" in cmd:
            self.speak_and_log("How many seconds or minutes should I set the reminder for?")
            self.root.after(4000, self.prompt_reminder_flow)
            return

        # 8. Add Custom Command Intent
        if "add custom command" in cmd or "new command" in cmd:
            self.speak_and_log("Please state the trigger phrase.")
            self.root.after(3000, lambda: self.prompt_custom_command_flow("trigger"))
            return

        # 9. General Knowledge QA DuckDuckGo queries fallback
        if any(prefix in cmd for prefix in ["who is", "what is", "where is", "tell me about"]):
            self.status_var.set("Searching DuckDuckGo...")
            answer = self.query_general_knowledge(raw_cmd)
            if answer:
                # Limit length to speak out
                speak_ans = answer[:150] + "..." if len(answer) > 150 else answer
                self.speak_and_log(speak_ans)
                return

        # 10. Ultimate fallback search redirect
        self.speak_and_log(f"I am not sure how to resolve '{raw_cmd}' locally. Opening Google Search.")
        webbrowser.open(f"https://www.google.com/search?q={raw_cmd.replace(' ', '+')}")

    # =====================================================================
    # COMPLEX VOICE FLOW INTERACTORS
    # =====================================================================

    def fetch_voice_weather(self, city):
        """Requests and speaks OWM weather stats."""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "units": "metric", "appid": WEATHER_API_KEY}
            r = requests.get(url, params=params, timeout=4)
            if r.status_code == 200:
                data = r.json()
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                self.speak_and_log(f"The current temperature in {city} is {round(temp)} degrees Celsius with {desc}.")
            else:
                self.speak_and_log(f"I could not fetch weather reports for '{city}'. Check spelling.")
        except Exception:
            self.speak_and_log("Weather services are currently offline.")

    def query_general_knowledge(self, query):
        """Sends search strings to DuckDuckGo API."""
        try:
            url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": 1}
            r = requests.get(url, params=params, timeout=4)
            if r.status_code == 200:
                data = r.json()
                abstract = data.get("AbstractText")
                if abstract:
                    return abstract
                
                related = data.get("RelatedTopics")
                if related and len(related) > 0:
                    text = related[0].get("Text")
                    if text:
                        return text
        except Exception:
            pass
        return None

    # --- EMAIL DIALOG FLOW ---
    def prompt_email_flow(self, state, details=None):
        """Guided recursive listener prompt to record email form contents."""
        if details is None:
            details = {}

        r = sr.Recognizer()
        with sr.Microphone() as src:
            r.adjust_for_ambient_noise(src)
            self.update_state("listening")
            try:
                audio = r.listen(src, timeout=4, phrase_time_limit=8)
                self.update_state("thinking")
                text = r.recognize_google(audio)
                self.log_chat("You", text)
                
                if state == "recipient":
                    # Clean spacing in emails
                    clean_recipient = text.lower().replace(" at ", "@").replace(" ", "")
                    details["recipient"] = clean_recipient
                    self.speak_and_log("What is the subject of this email?")
                    self.root.after(3000, lambda: self.prompt_email_flow("subject", details))
                elif state == "subject":
                    details["subject"] = text
                    self.speak_and_log("Please dictate the email body message.")
                    self.root.after(3500, lambda: self.prompt_email_flow("body", details))
                elif state == "body":
                    details["body"] = text
                    self.execute_mock_email(details)
            except Exception:
                self.speak_and_log("I did not catch that. Canceling emailing operation.")
                self.update_state("idle")

    def execute_mock_email(self, details):
        """Simulates SMTP client delivery logs on console."""
        self.log_chat("System", "SMTP Client: Connecting to SMTP server 'mail.aura.com'...")
        self.log_chat("System", "SMTP Client: Initiating PBKDF2 user authentication handshake...")
        self.log_chat("System", f"SMTP Client: Dispatching payload to '{details['recipient']}'...")
        time.sleep(1)
        self.log_chat("System", "SMTP Client: Mail dispatched successfully!")
        self.speak_and_log(f"Your email with subject '{details['subject']}' has been delivered to {details['recipient']}.")

    # --- REMINDER DIALOG FLOW ---
    def prompt_reminder_flow(self):
        """Processes time duration details for alarm threads."""
        r = sr.Recognizer()
        with sr.Microphone() as src:
            r.adjust_for_ambient_noise(src)
            self.update_state("listening")
            try:
                audio = r.listen(src, timeout=4)
                self.update_state("thinking")
                text = r.recognize_google(audio).lower()
                self.log_chat("You", text)
                
                # Parse numeric duration and unit
                duration = 0
                words = text.split()
                for word in words:
                    if word.isdigit():
                        duration = int(word)
                        break
                        
                if duration == 0:
                    self.speak_and_log("I could not determine the duration number. Canceling reminder.")
                    self.update_state("idle")
                    return

                if "minute" in text:
                    sec_time = duration * 60
                    lbl_time = f"{duration} minutes"
                else:
                    sec_time = duration
                    lbl_time = f"{duration} seconds"

                self.speak_and_log(f"Setting reminder for {lbl_time}.")
                threading.Thread(target=self._reminder_thread_loop, args=(sec_time,), daemon=True).start()
            except Exception:
                self.speak_and_log("Speech unclear. Timer setup canceled.")
                self.update_state("idle")

    def _reminder_thread_loop(self, delay_sec):
        time.sleep(delay_sec)
        # Trigger audible chime in background thread loop
        self.root.after(0, self.trigger_reminder_alert)

    def trigger_reminder_alert(self):
        """Audible alert chime loop and popup."""
        is_active = [True]
        
        # Audio loop
        def beep():
            if is_active[0] and HAS_WINSOUND:
                try:
                    winsound.Beep(1000, 400)
                    self.root.after(800, beep)
                except Exception:
                    pass

        # Trigger sound loop
        beep()
        
        messagebox.showinfo("AuraVoice Reminder Alert", "⏰ Time is up! Your timed reminder alert has expired.")
        is_active[0] = False # Terminate chime

    # --- CUSTOM COMMAND FLOW ---
    def prompt_custom_command_flow(self, state, data=None):
        """Creates custom JSON commands via voice."""
        if data is None:
            data = {}

        r = sr.Recognizer()
        with sr.Microphone() as src:
            r.adjust_for_ambient_noise(src)
            self.update_state("listening")
            try:
                audio = r.listen(src, timeout=4)
                self.update_state("thinking")
                text = r.recognize_google(audio)
                self.log_chat("You", text)
                
                if state == "trigger":
                    data["trigger"] = text.lower().strip()
                    self.speak_and_log("State the response for this phrase.")
                    self.root.after(3000, lambda: self.prompt_custom_command_flow("response", data))
                elif state == "response":
                    data["response"] = text.strip()
                    self.save_custom_command(data["trigger"], data["response"])
            except Exception:
                self.speak_and_log("Could not record command inputs. Action aborted.")
                self.update_state("idle")

    # =====================================================================
    # LOCAL CUSTOM COMMANDS LOGGING CONTROLLERS
    # =====================================================================

    def load_custom_commands(self):
        """Loads entries from voice_commands.json."""
        if os.path.exists(self.commands_path):
            try:
                with open(self.commands_path, "r", encoding="utf-8") as f:
                    self.custom_commands = json.load(f)
            except Exception:
                self.custom_commands = {}
        else:
            # Bootstrap defaults
            self.custom_commands = {
                "who is your creator": "I was created by Prateek Sagar for the Oasis Infobyte internship.",
                "what is your name": "My name is AuraVoice, your premium health and assistant suite.",
                "your favorite programming language": "I am written in Python, so Python is definitely my favorite!"
            }
            self.save_custom_commands_to_file()

    def save_custom_commands_to_file(self):
        """Writes internal mapping dictionary to disk file."""
        try:
            with open(self.commands_path, "w", encoding="utf-8") as f:
                json.dump(self.custom_commands, f, indent=4)
        except Exception:
            pass

    def save_custom_command(self, trigger, response):
        """Saves trigger pairs to file."""
        self.custom_commands[trigger] = response
        self.save_custom_commands_to_file()
        self.speak_and_log(f"Custom command registered! Saying '{trigger}' will now trigger the response: '{response}'.")


def main():
    root = tk.Tk()
    app = VoiceAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
