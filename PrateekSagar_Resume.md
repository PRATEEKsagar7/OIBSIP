# PRATEEK SAGAR
📍 Uttam Nagar, Delhi, India  
✉️ [prateeksagar640@gmail.com](mailto:prateeksagar640@gmail.com) | 🔗 [LinkedIn Profile](https://www.linkedin.com/in/parteek-sagar-4561ab38b) | 💻 [GitHub Portfolio](https://github.com/PRATEEKsagar7)

---

## PROFESSIONAL SUMMARY
Passionate and motivated **Bachelor of Computer Applications (BCA)** student with hands-on experience in **Python Software Development** and **Cybersecurity**. eJPT-certified Junior Penetration Tester with strong capabilities in network socket programming, database systems, dynamic visual GUIs, and ethical hacking fundamentals. Proven track record of building secure, multi-threaded desktop suites and forecast tools.

---

## EDUCATION
**Bachelor of Computer Applications (BCA)**  
*Expected Graduation: 2028*  
*Delhi, India*

---

## CERTIFICATIONS
* **eLearnSecurity Junior Penetration Tester (eJPT)** – Credentials in network security, system reconnaissance, and penetration testing methodologies.
* **Python Development Intern** – Oasis Infobyte (Completion: July 2026).

---

## TECHNICAL SKILLS
* **Programming Languages**: Python, HTML, CSS, JavaScript, SQL.
* **Libraries & Frameworks**: Tkinter (Desktop GUI), Matplotlib, PIL (Pillow), requests, Socket (TCP/IP), Pyttsx3, SpeechRecognition.
* **Database & Persistence**: SQLite3, relational schema design, JSON, CSV reporting.
* **Developer Tools & Workflow**: Git, GitHub, Threading (Parallel Execution), Command Line (Shell/PowerShell).
* **Security & Cryptography**: Salted Password Hashing (PBKDF2-HMAC-SHA256), Network Packet Analysis, OWASP Top 10 reconnaissance.

---

## PROFESSIONAL EXPERIENCE
**Python Development Intern** | *Oasis Infobyte*  
*July 2026 – Present (Remote)*
* Built and structured five advanced graphical desktop applications, delivering cleanly formatted Python source codes in a unified, Git-versioned submission repository.
* Implemented multithreading, API integrations, and persistent SQLite relational database schemas across multiple projects.
* Documented technical parameters and security disclosures in Markdown readmes, scoring highly on organizational clarity.

---

## TECHNICAL PROJECTS

### 💬 AuraChat – Multi-Room Socket Messaging Suite
*Developed a real-time messaging application connecting clients over a custom TCP socket server.*
* **Architecture**: Engineered a unified startup launcher containing both the Multi-threaded Server Monitor and the Client GUI Chat Dashboard.
* **Framing Protocol**: Resolved TCP stream fragmentation using a 4-byte length-prefix header preceding JSON data packets.
* **Security Registry**: Built a local login system storing PBKDF2-HMAC-SHA256 hashed and salted credentials in SQLite.
* **Alert systems**: Monitored GUI window focus state, triggering Winsound alert chimes and flashing title bars (`💬 * NEW MSG *`) for background messages.
* **Highlights**: Integrated an emoji translation system and auto-loaded the last 50 historical messages from SQLite on room joins.

### 🎙️ AuraVoice – Intelligent Voice Assistant
*Built an interactive desktop virtual assistant using voice recognition and text-to-speech feedback.*
* **Sine-wave Visualizer**: Programmed a Tkinter Canvas drawing a smooth sine-wave animation that adapts its amplitude/frequency to represent idle, listening, processing, and speaking states.
* **Thread-safe TTS**: Directed Pyttsx3 voice synthesis through a background queue worker thread to eliminate GUI freezing.
* **Natural Language Intent**: Classified vocal commands via NLU regex, integrating DuckDuckGo Instant Answer API for QA search queries and OpenWeatherMap for live reports.
* **Features**: Formulated a voice-guided email dictation wizard and set up threaded timer alarms.

### ☀️ AuraWeather – Real-Time Weather Suite
*Created a visual weather forecast dashboard utilizing coordinates, geolocators, and geolocation services.*
* **IP Detection**: Triangulated current user city on launch via IP address geocoding APIs.
* **Dynamic Styling**: Automatically mapped UI theme colors, borders, and gradients to current weather states (Clear sun, Grey cloudiness, Slate rain, Fog mist).
* **Icon Caching**: Coded a PIL/Pillow image fetcher to download and cache OpenWeatherMap CDN condition icons.

### 🔑 AuraPass – Secure Password Suite
*Designed a cryptographically secure password manager utilizing secrets entropy.*
* Enforced complexity filters using `secrets` and a secure Fisher-Yates shuffle.
* Calculated mathematical Shannon entropy, displaying a 4-tier colored strength bar.
* Built a masked session history viewer (`••••••••`) with reveal toggles.

### 📊 AuraBMI – Premium Health Analytics Dashboard
*Designed a multi-user health analytics program plotting weight histories.*
* Custom canvas needle gauge displays dynamic classifications.
* Integrated Matplotlib trend lines showing healthy target zones as colored background bands.
