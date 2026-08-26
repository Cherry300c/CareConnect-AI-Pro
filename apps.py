import plotly.express as px
import streamlit as st

from ai_engine import render_chatbot, render_prescription_reader
from auth import current_user, login_user, logout_user, register_user
from config import APP_DISCLAIMER, APP_NAME
from dashboard_engine import (
    render_admin_dashboard,
    render_doctor_queue,
    render_feedback,
    render_health_tips,
    render_patient_history,
)
from database import init_db, seed_admin
from location_engine import render_hospital_locator
from reminder_engine import render_followups, render_medicine_reminders
from report_engine import render_report_center
from triage_engine import render_symptom_triage


st.set_page_config(
    page_title=APP_NAME,
    page_icon="CC",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
.stApp {
    background:
        linear-gradient(135deg, rgba(15,118,110,.13), transparent 34rem),
        linear-gradient(180deg, #f8fafc 0%, #edf7f5 100%);
    color: #0f172a;
}
.block-container {
    max-width: 1280px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}
.hero {
    min-height: 240px;
    border-radius: 16px;
    padding: 28px 32px;
    color: white;
    background:
        linear-gradient(135deg, rgba(15,118,110,.96), rgba(14,116,144,.92)),
        url("https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1600&q=80");
    background-size: cover;
    background-position: center;
    box-shadow: 0 18px 48px rgba(15,118,110,.22);
    border: 1px solid rgba(255,255,255,.2);
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    margin-bottom: 20px;
}
.hero h1 {
    margin: 0 0 8px 0;
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: 1px;
    text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
    color: white;
}
.hero p {
    margin: 0;
    max-width: 900px;
    font-size: 1.1rem;
    color: rgba(255,255,255,.92);
}
.panel {
    background: rgba(255,255,255,0.75);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid #dbe3ea;
    border-radius: 15px;
    padding: 18px;
    box-shadow: 0 12px 30px rgba(15,23,42,.06);
    margin-bottom: 16px;
}
.mini-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 10px;
}
.metric-card {
    background: rgba(255,255,255,.97);
    border: 1px solid #dbe3ea;
    border-radius: 15px;
    padding: 18px;
    min-height: 122px;
    box-shadow: 0 12px 30px rgba(15,23,42,.06);
}
.section-title {
    margin: 0 0 8px 0;
    font-weight: 800;
    font-size: 1.04rem;
}
.section-copy {
    color: #64748b;
    font-size: .93rem;
}
.badge {
    display: inline-flex;
    border-radius: 999px;
    padding: 7px 12px;
    font-weight: 800;
    font-size: .84rem;
}
.badge-low { color: #166534; background: #dcfce7; }
.badge-medium { color: #92400e; background: #fef3c7; }
.badge-high { color: #991b1b; background: #fee2e2; }
.call-card {
    display: block;
    text-decoration: none;
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fecaca;
    border-radius: 12px;
    padding: 16px;
    margin-top: 8px;
}
.call-card strong {
    display: block;
    font-size: 1.2rem;
}
.call-card span {
    color: #7f1d1d;
}
.stButton > button {
    border-radius: 12px;
    min-height: 2.7rem;
    border: 0;
    background: linear-gradient(135deg, #0f766e, #0891b2);
    color: white;
    font-weight: 800;
    transition: 0.3s;
}
.stButton > button:hover {
    color: white;
    filter: brightness(.98);
    transform: scale(1.05);
}
.stTabs [data-baseweb="tab"]{
    font-size:15px;
    font-weight:700;
    border-radius:10px;
    padding:10px 18px;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"]{
    border-radius:12px !important;
    border:1px solid #cbd5e1 !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus{
    border-color:#0891b2 !important;
}

div[data-testid="stMetric"]{
    background:white;
    padding:15px;
    border-radius:15px;
    box-shadow:0 6px 20px rgba(0,0,0,0.08);
}
</style>
"""

app_translations = {
    "English": {
        "login_hero": "Advanced rural healthcare assistant with triage, prescriptions, appointments, maps, reminders, dashboards, reports, and patient history.",
        "app_hero": "Clinical triage, AI prescription reading, hospital locator, reports and reminders.",
        "patient_tabs": [
            "Symptom Triage",
            "Prescription Reader",
            "Hospital Locator",
            "Appointments & Reports",
            "Medicine Reminders",
            "History",
            "Chatbot",
            "Health Tips",
            "Feedback",
        ],
        "doctor_tabs": ["Doctor Queue", "Patient Search", "Disease Trends", "Reports", "Health Tips"],
        "admin_tabs": ["Admin Analytics", "Doctor Queue", "Patient Records", "Feedback", "Exports"],
        "signed_in": "Signed in as",
        "logout_btn": "Logout"
    },
    "Telugu": {
        "login_hero": "ట్రయాజ్, ప్రిస్క్రిప్షన్లు, అపాయింట్‌మెంట్‌లు, మ్యాప్‌లు, రిమైండర్‌లు, డాష్‌బోర్డ్‌లు, నివేదికలు మరియు రోగి చరిత్రతో కూడిన అధునాతన గ్రామీణ ఆరోగ్య సంరక్షణ సహాయకుడు.",
        "app_hero": "క్లినికల్ ట్రయాజ్, AI ప్రిస్క్రిప్షన్ రీడింగ్, ఆసుపత్రి శోధన, నివేదికలు మరియు రిమైండర్లు.",
        "patient_tabs": [
            "లక్షణాల ట్రయాజ్ (Symptom Triage)",
            "ప్రిస్క్రిప్షన్ రీడర్ (Prescription Reader)",
            "ఆసుపత్రి శోధన (Hospital Locator)",
            "అపాయింట్‌మెంట్‌లు & నివేదికలు",
            "మందుల రిమైండర్‌లు",
            "రోగి చరిత్ర",
            "చాట్‌బాట్ (Chatbot)",
            "ఆరోగ్య చిట్కాలు",
            "అభిప్రాయం (Feedback)",
        ],
        "doctor_tabs": ["వైద్యుల క్యూ", "రోగి శోధన", "వ్యాధి ట్రెండ్స్", "నివేదికలు", "ఆరోగ్య చిట్కాలు"],
        "admin_tabs": ["అడ్మిన్ విశ్లేషణలు", "వైద్యుల క్యూ", "రోగి రికార్డులు", "అభిప్రాయం", "ఎగుమతులు"],
        "signed_in": "లాగిన్ అయ్యారు:",
        "logout_btn": "లాగౌట్"
    },
    "Hindi": {
        "login_hero": "ट्रायज, नुस्खे, अपॉइंटमेंट, मानचित्र, अनुस्मारक, डैशबोर्ड, report और रोगी के इतिहास के साथ उन्नत ग्रामीण स्वास्थ्य देखभाल सहायक।",
        "app_hero": "क्लिनिकल ट्रायज, AI प्रिस्क्रिप्शन रीडिंग, अस्पताल खोज, रिपोर्ट और रिमाइंडर।",
        "patient_tabs": [
            "लक्षण ट्रायज (Symptom Triage)",
            "प्रिस्क्रिप्शन रीडर (Prescription Reader)",
            "अस्पताल खोजक (Hospital Locator)",
            "अपॉइंटमेंट और रिपोर्ट",
            "दवा अनुस्मारक",
            "इतिहास (History)",
            "चैटबॉट (Chatbot)",
            "स्वास्थ्य सुझाव",
            "प्रतिक्रिया (Feedback)",
        ],
        "doctor_tabs": ["डॉक्टर कतार", "रोगी खोज", "रोग रुझान", "रिपोर्ट", "स्वास्थ्य सुझाव"],
        "admin_tabs": ["एडमिन एनालिटिक्स", "डॉक्टर कतार", "रोगी रिकॉर्ड", "प्रतिक्रिया", "निर्यात"],
        "signed_in": "के रूप में साइन इन हैं:",
        "logout_btn": "लॉगआउट"
    }
}


def init_session():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("last_assessment", None)
    st.session_state.setdefault("selected_facility", None)
    st.session_state.setdefault("nearby_facilities", [])
    st.session_state.setdefault("last_booking", None)
    st.session_state.setdefault("last_prescription_result", None)
    st.session_state.setdefault("language", "English")


def render_hero(copy):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="hero">
            <h1>CareConnect AI Pro</h1>
            <p>{copy}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page():
    lang = st.session_state.get("language", "English")
    render_hero(app_translations[lang]["login_hero"])

    login_tab, register_tab = st.tabs(["Login", "Register"])
    with login_tab:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Sign in")
        st.caption("Demo admin: admin@careconnect.local / admin123")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", use_container_width=True):
            user = login_user(email, password)
            if user:
                st.session_state.user = user
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid email or password.")
        st.markdown("</div>", unsafe_allow_html=True)

    with register_tab:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Create account")
        name = st.text_input("Full name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        phone = st.text_input("Phone", key="reg_phone")
        password = st.text_input("Password", type="password", key="reg_password")
        role = st.selectbox("Role", ["Patient", "Doctor"], key="reg_role")
        if st.button("Register", use_container_width=True):
            ok, message = register_user(name, email, phone, password, role)
            st.success(message) if ok else st.error(message)
        st.markdown("</div>", unsafe_allow_html=True)

    st.info(APP_DISCLAIMER)


def render_header(user):
    lang = st.session_state.get("language", "English")
    render_hero(app_translations[lang]["app_hero"])
    
    c1, c2 = st.columns([1, 0.18])
    with c1:
        st.caption(f"{app_translations[lang]['signed_in']} {user['name']} - {user['role']}")
    with c2:
        if st.button(app_translations[lang]["logout_btn"], use_container_width=True):
            logout_user()
            st.rerun()
            
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("🤖 AI Chatbot", "Active")
    with mc2:
        st.metric("🏥 Hospital Locator", "Ready")
    with mc3:
        st.metric("📅 Appointments", "Available")
    with mc4:
        st.metric("💊 Prescription AI", "Online")
        
    st.info(APP_DISCLAIMER)


def render_patient_app(user):
    lang = st.session_state.get("language", "English")
    tabs = st.tabs(app_translations[lang]["patient_tabs"])
    
    with tabs[0]:
        render_symptom_triage(user)
    with tabs[1]:
        render_prescription_reader(user)
    with tabs[2]:
        render_hospital_locator(user)
    with tabs[3]:
        render_report_center(user)
    with tabs[4]:
        render_medicine_reminders(user)
        render_followups(user)
    with tabs[5]:
        render_patient_history(user)
    with tabs[6]:
        render_chatbot(user)
    with tabs[7]:
        render_health_tips()
    with tabs[8]:
        render_feedback(user)


def render_doctor_app(user):
    lang = st.session_state.get("language", "English")
    tabs = st.tabs(app_translations[lang]["doctor_tabs"])
    
    with tabs[0]:
        render_doctor_queue(user)
    with tabs[1]:
        render_patient_history(user, doctor_mode=True)
    with tabs[2]:
        render_admin_dashboard(user, doctor_view=True)
    with tabs[3]:
        render_report_center(user)
    with tabs[4]:
        render_health_tips()


def render_admin_app(user):
    lang = st.session_state.get("language", "English")
    tabs = st.tabs(app_translations[lang]["admin_tabs"])
    
    with tabs[0]:
        render_admin_dashboard(user)
    with tabs[1]:
        render_doctor_queue(user)
    with tabs[2]:
        render_patient_history(user, doctor_mode=True)
    with tabs[3]:
        render_feedback(user, admin_mode=True)
    with tabs[4]:
        render_report_center(user, admin_mode=True)


def main():
    init_db()
    seed_admin()
    init_session()

    st.sidebar.markdown("""
<div style="
background:linear-gradient(135deg,#0f766e,#0891b2);
padding:15px;
border-radius:12px;
text-align:center;
color:white;">
<h2>🏥 CareConnect AI Pro</h2>
<p>AI Healthcare Assistant</p>
</div>
""", unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    language = st.sidebar.selectbox(
        "🌐 Select Language / భాషను ఎంచుకోండి / भाषा चुनें",
        ["English", "Telugu", "Hindi"],
        index=["English", "Telugu", "Hindi"].index(st.session_state.get("language", "English"))
    )
    st.session_state["language"] = language

    user = current_user()
    if not user:
        render_login_page()
        return

    render_header(user)
    if user["role"] == "Patient":
        render_patient_app(user)
    elif user["role"] == "Doctor":
        render_doctor_app(user)
    else:
        render_admin_app(user)

    st.markdown("""
<hr>
<center>
CareConnect AI Pro © 2026
<br>
AI-Powered Healthcare Assistance Platform
</center>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()