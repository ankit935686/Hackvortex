# Hackvortex 
# 🏙️ Smart City Dashboard

An integrated, web-based platform that brings real-time data, citizen feedback, and IoT-driven environmental insights into one unified dashboard. Built to empower city administrators, enhance citizen participation, and make urban governance smarter, safer, and more sustainable.

---

## 📌 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [How It Works](#-how-it-works)
- [Installation & Setup](#-installation--setup)
- [APIs Used](#-apis-used)
- [IoT Integration](#-iot-integration)
- [Future Scope](#-future-scope)
- [Video Link](#-screenshots)
- [Contributors](#-contributors)
-

---

## 🚀 Features

- 📡 Real-time pollution & smoke level monitoring using IoT sensors (Arduino + gas sensors)
- 🗺️ Dynamic traffic routing using Google Maps API
- 🌤️ Live weather and AQI updates via OpenWeather and AirVisual APIs
- 🧾 Smart complaint system for citizens to report civic issues
- 📊 Admin dashboard with data analytics and real-time reports
- 🤖 AI assistant powered by Google Gemini API for intelligent interaction
- 🌍 Multilingual support through Google Translate API
- 🚨 Emergency Voice Assistance (Unique Feature)

  → In case of an emergency, users can press and hold a button and speak their issue (e.g., “medical emergency”).

  - Gemini API analyzes the voice input and identifies the type of emergency.
  - The system responds calmly to reassure the user.
  - It displays the nearest relevant service (e.g., hospital for medical emergencies) using Google Maps.
  - Provides emergency contact numbers.
  - Allows users to share their live location with saved contacts.
---

## 🧠 Tech Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Django (Python)

### APIs
- Google Maps API
- OpenWeather API
- AirVisual API
- Google Gemini API
- Google Translate API

### Others
- AJAX & JSON (for dynamic updates)
- Chart.js (for data visualization)

---

## ⚙️ How It Works

1. 🧪 Sensors collect real-time environmental data (pollution, smoke).
2. 🔄 Data is transmitted to the backend using serial communication.
3. 💾 Django processes and stores the data.
4. 🧑‍💻 Citizens can view weather, traffic, and AQI reports and file complaints.
5. 📈 Admins access real-time reports, citizen feedback, and visual insights.
6. 🤖 AI and multilingual support enhance user experience and accessibility.

---
---

## 🌐 APIs Used

- 🗺️ Google Maps API – For live traffic visualization, shortest route suggestions, and location-based services
- 🌫️ AirVisual API – Provides real-time air quality index (AQI) and pollution data
- 🌤️ OpenWeather API – Supplies weather conditions including temperature and humidity
- 🌐 Google Translate API – Enables multilingual support for diverse citizen access
- 🤖 Google Gemini API – Powers AI-driven interaction for smart assistance and emergency voice commands

---

## 🔌 IoT Integration

- 🔧 Arduino UNO with MQ-series gas sensors
- 🌫️ Captures real-time smoke and air pollution levels
- 🔄 Sends sensor data to the Django backend for live visualization and alerts in the dashboard

---

## 🌱 Future Scope

- 🚑 Integration with real-world emergency response systems (e.g., ambulance dispatch, police coordination)
- 📊 Predictive analytics using machine learning to forecast traffic, pollution, or emergencies
- 🔊 Expanded IoT sensor network (e.g., noise, light, flood detection)
- 📱 Mobile application for enhanced accessibility and portability
- 📂 Open data APIs for research, policymaking, and third-party integrations

---

## 🎥 Demo Video

Watch our live demonstration video of the Smart City Dashboard in action:

🔗 [Click here to view the demo](https://your-video-link.com)  
(Add your video link once uploaded to YouTube, Google Drive, or another hosting platform.)

---

## 👨‍💻 Contributors

- 💻 [Swayam Chaudhari] – Frontend Development/ UI/UX Design & Documentation
- 🧠 [Ankit Satpute] – Backend & API Integration
- 🔌 [Harsh Dalvi] – IoT Hardware & Sensor Implementation
- 


## 🛠️ Installation & Setup

```bash
# Clone the repository
git clone https://github.com/ankit935686/Hackvortex.git

# Navigate to the project directory
cd smart-city-dashboard

# Install dependencies
pip install -r requirements.txt

# Run the server
python manage.py runserver
