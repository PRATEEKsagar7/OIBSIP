# Oasis Infobyte Python Development Internship (OIBSIP)

Welcome to my submission repository for the Oasis Infobyte Python Development Internship. This repository contains advanced graphical desktop applications built using Python, `tkinter`, and standard libraries.

---

## Repository Contents & File Names

- **Task 2: Body Mass Index (BMI) Calculator**
  - **Filename:** [PrateekSagar_Task2.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task2.py)
- **Task 3: Cryptographically Secure Password Generator**
  - **Filename:** [PrateekSagar_Task3.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task3.py)
- **Task 4: Real-Time Weather Forecast Application**
  - **Filename:** [PrateekSagar_Task4.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task4.py)
- **Task 5: Multi-Room Socket Chat Application**
  - **Filename:** [PrateekSagar_Task5.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task5.py)

---

## Project Details

### 📊 Task 2: AuraBMI - Premium Health Suite
An advanced, multi-featured desktop BMI calculator featuring a modern dashboard design, history trend lines, and user profile management.
* **Core Features**:
  * **Dynamic Canvas Gauge**: Draws an animated semi-circle speedometer showing the BMI range with colors.
  * **Dual Units**: Metric (kg/cm) and Imperial (lbs/feet-inches) with instant unit conversions.
  * **Profile CRUD**: Create named profiles; switch profiles to load past summaries; delete profiles.
  * **Interactive Line Charts**: Embedded matplotlib visualization with color-banded healthy BMI zones.

---

### 🔑 Task 3: AuraPass - Cryptographically Secure Password Suite
A cryptographically secure desktop password generator equipped with complexity settings, entropy meters, and visual history logs.
* **Core Features**:
  * **Secrets Cryptography**: Uses system entropy (`secrets`) with a custom secure Fisher-Yates shuffle.
  * **Shannon Entropy Analysis**: Computes mathematical password entropy live and renders a 4-tier colored bar.
  * **Inclusion Guarantee**: Enforces rules guaranteeing that at least one character from every selected category is included.
  * **Masked Session Logs**: Memory-only list tracking the last 5 passwords, masked with bullet points for visual security, alongside reveal toggles and individual copy actions.

---

### ☀️ Task 4: AuraWeather - Real-Time Weather Suite
A sleek desktop weather forecast dashboard featuring local geolocation detection and responsive visual weather themes.
* **Core Features**:
  * **Auto-Geolocation**: Automatically queries your local city on launch using IP address triangulation via `ipinfo.io`.
  * **Dynamic Weather Themes**: Background colors and borders change depending on the condition (sunny yellow, rainy slate, cloudy grey, frosty snow).
  * **Hourly Forecast Panel**: Shows current temperature forecasts for the next 6 hours in 3-hour increments.
  * **Daily Forecast Grid**: Computes future daily weekdays showing min/max ranges and dominant conditions.

---

### 💬 Task 5: AuraChat - Multi-Room Messaging Suite
A real-time messaging application with user authentication, custom chat rooms, and persistent message logs, packaged as a unified executable.
* **Core Features**:
  * **Dual-Mode Startup**: Run either the Server Monitor console or Client interface from the same Python script launcher.
  * **Threaded JSON socket protocol**: Handles multiple client connections concurrently over TCP, using length-prefixed JSON messaging to avoid packet splitting.
  * **Emoji translation**: Translates common text shortcodes (e.g. `:smile:`, `:heart:`) to Unicode.
  * **Alert triggers**: Flashes window titles and plays asterisk alert chimes when a new message arrives and the window is unfocused.
  * **Room History**: Automatically caches and loads the last 50 room messages from SQLite upon joining.

#### 🛡️ Security Transparency Disclosure (E2E Awareness)
* **Message Transmission**: Sockets transmit JSON strings encoded as raw UTF-8. **There is no End-to-End (E2E) message encryption in transit.** Payloads can be intercepted by network packets sniffers on the same local network subnet.
* **Local Storage**: Historical room messages are saved as plain text within `chat_history.db` on the server host to enable quick history fetches.
* **Logins Registry**: User credentials are secure. Passwords undergo pbkdf2 salted hashing (`PBKDF2-HMAC-SHA256` with random 16-byte unique salts) prior to SQLite storage, preventing credential theft in the event of database leaks.

---

## How to Run the Applications

### Prerequisites
Make sure you have Python 3.11+ installed. Install the external dependencies using pip:
```bash
pip install matplotlib requests pillow pyperclip
```

### Execution
Run any task script directly using Python:

```bash
# Run Task 2 (BMI Calculator)
python PrateekSagar_Task2.py

# Run Task 3 (Password Generator)
python PrateekSagar_Task3.py

# Run Task 4 (Weather App)
python PrateekSagar_Task4.py

# Run Task 5 (Chat Application)
# Launch Server on one terminal, then launch Clients on others
python PrateekSagar_Task5.py
```
