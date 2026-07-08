# Oasis Infobyte Python Development Internship (OIBSIP)

Welcome to my submission repository for the Oasis Infobyte Python Development Internship. This repository contains three advanced graphical desktop applications built using Python, `tkinter`, and standard libraries.

---

## Repository Contents & File Names

- **Task 1: Body Mass Index (BMI) Calculator**
  - **Filename:** [PrateekSagar_Task1.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task1.py)
- **Task 2: Cryptographically Secure Password Generator**
  - **Filename:** [PrateekSagar_Task2.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task2.py)
- **Task 3: Real-Time Weather Forecast Application**
  - **Filename:** [PrateekSagar_Task3.py](file:///c:/Users/prateek%20sagar/.vscode/OIBSIP/PrateekSagar_Task3.py)

---

## Project Details

### 📊 Task 1: AuraBMI - Premium Health Suite
An advanced, multi-featured desktop BMI calculator featuring a modern dashboard design, history trend lines, and user profile management.

* **Tech Stack**: Python, `tkinter` (`ttk`), `sqlite3`, `matplotlib`, `csv`
* **Core Features**:
  * **Dynamic Canvas Gauge**: Draws an animated semi-circle speedometer showing the BMI range with colors.
  * **Dual Units**: Metric (kg/cm) and Imperial (lbs/feet-inches) with instant unit conversions.
  * **Ideal Target recommendation**: Computes target healthy weights customized to your height.
  * **Profile CRUD**: Create named profiles; switch profiles to load past summaries; delete profiles.
  * **Interactive Line Charts**: Embedded matplotlib visualization with color-banded healthy BMI zones.
  * **History Manager & CSV Export**: Check full list logs, delete single entries, or export reports to CSV files.

---

### 🔑 Task 2: AuraPass - Cryptographically Secure Password Suite
A cryptographically secure desktop password generator equipped with complexity settings, entropy meters, and visual history logs.

* **Tech Stack**: Python, `secrets`, `pyperclip`, `tkinter`, `math`
* **Core Features**:
  * **Secrets Cryptography**: Uses system entropy (`secrets`) with a custom secure Fisher-Yates shuffle.
  * **Synchronized Length Selectors**: Linked slider and spinbox length selectors (8–64 character limits).
  * **Shannon Entropy Analysis**: Computes mathematical password entropy live and renders a 4-tier colored bar.
  * **Inclusion Guarantee**: Enforces rules guaranteeing that at least one character from every selected category is included.
  * **Ambiguous Character Exclusions**: Strips confusing look-alike characters (`0`, `O`, `o`, `1`, `I`, `l`, `|`).
  * **Masked Session Logs**: Memory-only list tracking the last 5 passwords, masked with bullet points for visual security, alongside reveal toggles and individual copy actions.

---

### ☀️ Task 3: AuraWeather - Real-Time Weather Suite
A sleek desktop weather forecast dashboard featuring local geolocation detection and responsive visual weather themes.

* **Tech Stack**: Python, `requests`, `PIL` (Pillow), `tkinter`
* **Core Features**:
  * **Auto-Geolocation**: Automatically queries your local city on launch using IP address triangulation via `ipinfo.io`.
  * **Weather Condition Icon Cache**: Downloads weather condition images via OpenWeatherMap and caches them in memory.
  * **Dynamic Weather Themes**: Background colors and borders change depending on the condition (sunny yellow, rainy slate, cloudy grey, frosty snow).
  * **Instant Unit Conversion**: Switch between °C and °F to immediately convert temperatures, wind speed, and visibility client-side.
  * **Hourly Forecast Panel**: Shows current temperature forecasts for the next 6 hours in 3-hour increments.
  * **Daily Forecast Grid**: Computes future daily weekdays showing min/max ranges and dominant conditions.

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
# Run Task 1 (BMI Calculator)
python PrateekSagar_Task1.py

# Run Task 2 (Password Generator)
python PrateekSagar_Task2.py

# Run Task 3 (Weather App)
python PrateekSagar_Task3.py
```
