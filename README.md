# CareConnect AI Pro

CareConnect AI Pro is an advanced rural healthcare support system built with Streamlit.

It combines symptom triage, AI guidance, prescription image reading, hospital/clinic discovery, appointment booking, reminders, reports, patient history, doctor queue management, and admin analytics.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Admin Login

Email: `admin@careconnect.local`

Password: `admin123`

## Gemini API

The app works without Gemini using safe fallback messages. To enable AI:

```bash
set GEMINI_API_KEY=your_key_here
```

## Project Structure

```text
CareConnectAI_Pro/
  app.py
  config.py
  database.py
  auth.py
  triage_engine.py
  ai_engine.py
  location_engine.py
  report_engine.py
  reminder_engine.py
  dashboard_engine.py
  requirements.txt
  README.md
```
