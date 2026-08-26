import pandas as pd
import streamlit as st

from ai_engine import get_ai_advice
from database import insert_record


CRITICAL_SYMPTOMS = {
    "chest pain",
    "breathing difficulty",
    "shortness of breath",
    "unconsciousness",
    "severe bleeding",
    "stroke symptoms",
    "seizure",
    "blue lips",
    "confusion",
}

# These symptoms increase urgency but do not, by themselves, mean emergency.
MODERATE_SYMPTOMS = {
    "fever",
    "vomiting",
    "diarrhea",
    "dizziness",
    "weakness",
    "dehydration",
    "persistent cough",
    "wheezing",
    "burning urination",
}

SEVERE_TERMS = {
    "high fever",
    "blood in vomit",
    "blood in stool",
    "coughing blood",
    "severe pain",
    "low urine",
}


FALLBACK_DISEASE_DATA = pd.DataFrame(
    [
        ["Common Cold", "cough", "sneezing", "runny nose", "mild fever"],
        ["Migraine", "headache", "nausea", "sensitivity to light", "vomiting"],
        ["Gastritis", "stomach pain", "nausea", "vomiting", "loss of appetite"],
        ["Respiratory Distress", "shortness of breath", "breathing difficulty", "chest pain", "wheezing"],
        ["Dehydration", "dizziness", "weakness", "dry mouth", "low urine"],
        ["Food Poisoning", "vomiting", "diarrhea", "stomach pain", "fever"],
        ["Flu", "fever", "body pain", "cough", "fatigue"],
        ["Hypertension Concern", "headache", "chest pain", "dizziness", "blurred vision"],
        ["Diabetes Concern", "frequent urination", "excessive thirst", "fatigue", "weight loss"],
        ["Skin Allergy", "itching", "rash", "redness", "swelling"],
        ["Dengue Concern", "high fever", "body pain", "rash", "low platelet"],
        ["Malaria Concern", "fever", "chills", "sweating", "weakness"],
        ["Anemia Concern", "fatigue", "pale skin", "dizziness", "shortness of breath"],
        ["Urinary Infection", "burning urination", "frequent urination", "lower abdomen pain", "fever"],
    ],
    columns=["Disease", "Symptom_1", "Symptom_2", "Symptom_3", "Symptom_4"],
)


FALLBACK_PRECAUTIONS = pd.DataFrame(
    [
        ["Common Cold", "Rest", "Drink warm fluids", "Monitor fever", "Consult doctor if symptoms worsen"],
        ["Migraine", "Rest in a dark room", "Hydrate", "Avoid loud noise", "Consult doctor if severe"],
        ["Gastritis", "Eat light food", "Avoid spicy meals", "Hydrate", "Seek care if pain persists"],
        ["Respiratory Distress", "Seek emergency care", "Keep patient upright", "Avoid exertion", "Call emergency services"],
        ["Dehydration", "Use ORS", "Drink clean water", "Rest", "Seek care if severe"],
        ["Food Poisoning", "Use ORS", "Avoid oily food", "Rest", "Seek care if dehydration appears"],
        ["Flu", "Rest", "Hydrate", "Monitor fever", "Avoid close contact"],
        ["Hypertension Concern", "Rest quietly", "Avoid exertion", "Check blood pressure", "Consult doctor"],
        ["Diabetes Concern", "Avoid sugary drinks", "Hydrate", "Monitor symptoms", "Consult doctor"],
        ["Skin Allergy", "Avoid triggers", "Do not scratch", "Keep area clean", "Consult doctor if spreading"],
        ["Dengue Concern", "Avoid painkillers without doctor advice", "Hydrate", "Monitor bleeding", "Get platelet test"],
        ["Malaria Concern", "Visit clinic for test", "Hydrate", "Use mosquito protection", "Complete prescribed medicines"],
        ["Anemia Concern", "Eat iron-rich food", "Avoid heavy exertion", "Get blood test", "Consult doctor"],
        ["Urinary Infection", "Drink water", "Avoid self-medication", "Do urine test", "Consult doctor if fever appears"],
    ],
    columns=["Disease", "Precaution_1", "Precaution_2", "Precaution_3", "Precaution_4"],
)


@st.cache_resource
def load_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


@st.cache_data
def load_datasets():
    try:
        disease_df = pd.read_csv("DiseaseAndSymptoms.csv")
        if "Disease" not in disease_df.columns:
            disease_df = FALLBACK_DISEASE_DATA
    except Exception:
        disease_df = FALLBACK_DISEASE_DATA

    try:
        precaution_df = pd.read_csv("Disease precaution.csv")
        if "Disease" not in precaution_df.columns:
            precaution_df = FALLBACK_PRECAUTIONS
    except Exception:
        precaution_df = FALLBACK_PRECAUTIONS

    return disease_df, precaution_df


@st.cache_data
def build_documents(disease_df):
    docs = []
    for _, row in disease_df.iterrows():
        disease = str(row.iloc[0]).strip()
        symptoms = row.iloc[1:].dropna().astype(str).unique()
        clean = [s.replace("_", " ").strip().lower() for s in symptoms if str(s).strip()]
        docs.append(f"The condition {disease} is commonly associated with these symptoms: {', '.join(clean)}.")
    return docs


@st.cache_resource
def build_embeddings(docs):
    model = load_model()
    if model is None:
        return None
    try:
        return model.encode(docs, convert_to_tensor=True)
    except Exception:
        return None


@st.cache_data
def build_symptom_scores(disease_df):
    # Dataset frequency is useful for prediction, but it does not measure danger.
    # Keep explicit clinical weights separate from disease retrieval.
    return {symptom: 0.5 for symptom in MODERATE_SYMPTOMS}


def parse_symptoms(text):
    return [item.strip().lower() for item in text.replace("\n", ",").split(",") if item.strip()]


def calculate_risk(symptoms, symptom_scores, age):
    if not symptoms:
        return "Low Risk", 0.0

    normalized = {symptom.replace("_", " ").strip().lower() for symptom in symptoms}
    symptom_text = " | ".join(normalized)

    if any(
        critical == symptom or critical in symptom
        for symptom in normalized
        for critical in CRITICAL_SYMPTOMS
    ):
        return "High Risk", 5.0

    score = 1.0
    score += min(
        sum(symptom_scores.get(symptom, 0.0) for symptom in normalized),
        1.0,
    )

    if age <= 5 or age >= 60:
        score += 0.75
    if len(symptoms) >= 5:
        score += 0.5
    if any(term in symptom_text for term in SEVERE_TERMS):
        score += 1.5

    score = min(score, 5.0)

    if score < 2:
        return "Low Risk", score
    if score < 4:
        return "Medium Risk", score
    return "High Risk", score


def lexical_retrieve_condition(symptoms, disease_df, docs):
    query_words = set(" ".join(symptoms).replace("_", " ").lower().split())
    best_idx = 0
    best_score = -1

    for idx, doc in enumerate(docs):
        doc_lower = doc.lower()
        doc_words = set(doc_lower.replace("_", " ").split())
        exact = sum(1 for symptom in symptoms if symptom in doc_lower)
        overlap = len(query_words & doc_words)
        score = exact * 4 + overlap
        if score > best_score:
            best_score = score
            best_idx = idx

    disease = disease_df.iloc[best_idx]["Disease"]
    context = docs[best_idx]
    confidence = max(25, min(94, round(35 + best_score * 7, 2)))
    return disease, context, confidence


def retrieve_condition(symptoms, disease_df, docs, embeddings):
    model = load_model()
    if model is None or embeddings is None:
        return lexical_retrieve_condition(symptoms, disease_df, docs)

    try:
        from sentence_transformers import util
        query = " ".join(symptoms)
        query_embedding = model.encode(query, convert_to_tensor=True)
        scores = util.pytorch_cos_sim(query_embedding, embeddings)
        idx = scores.argmax().item()
        similarity = float(scores[0][idx].item())
        context = docs[idx]
        disease = disease_df.iloc[idx]["Disease"]
        matched = sum(1 for symptom in symptoms if symptom in context.lower())
        match_ratio = matched / len(symptoms) if symptoms else 0
        confidence = round((0.7 * similarity + 0.3 * match_ratio) * 100, 2)
        return disease, context, max(0, min(100, confidence))
    except Exception:
        return lexical_retrieve_condition(symptoms, disease_df, docs)


def get_precautions(precaution_df, disease):
    row = precaution_df[precaution_df.iloc[:, 0].astype(str).str.lower() == str(disease).lower()]
    if row.empty:
        return ["No specific precautions found. Consult a medical professional."]
    return [str(value).capitalize() for value in row.iloc[0, 1:].dropna().values if str(value).strip()]


def risk_badge(risk):
    if risk == "High Risk":
        return '<span class="badge badge-high">High Risk</span>'
    if risk == "Medium Risk":
        return '<span class="badge badge-medium">Medium Risk</span>'
    return '<span class="badge badge-low">Low Risk</span>'


def recommend_specialist(disease):
    disease = disease.lower()

    specialist_map = {
        "migraine": "🧠 Neurologist",
        "headache": "🧠 Neurologist",
        "skin allergy": "🩺 Dermatologist",
        "eczema": "🩺 Dermatologist",
        "asthma": "🫁 Pulmonologist",
        "respiratory distress": "🫁 Pulmonologist",
        "hypertension concern": "❤️ Cardiologist",
        "heart attack": "❤️ Cardiologist",
        "diabetes concern": "🩸 Endocrinologist",
        "flu": "👨‍⚕️ General Physician",
        "common cold": "👨‍⚕️ General Physician",
        "gastritis": "🩺 Gastroenterologist",
        "malaria concern": "🦟 Infectious Disease Specialist",
        "dengue concern": "🦟 Infectious Disease Specialist",
        "urinary infection": "🩺 Urologist",
        "anemia concern": "🩸 Hematologist",
        "food poisoning": "🦟 Infectious Disease Specialist",
        "dehydration": "👨‍⚕️ General Physician",
    }

    return specialist_map.get(
        disease,
        "👨‍⚕️ General Physician"
    )


def patient_demographics_form(prefix, user):
    c1, c2 = st.columns([1, 1])
    with c1:
        patient_name = st.text_input("Patient name", value=user.get("name", ""), key=f"{prefix}_name")
    with c2:
        phone = st.text_input("Phone number", value=user.get("phone", ""), key=f"{prefix}_phone")

    d1, d2, d3 = st.columns(3)
    with d1:
        age = st.number_input("Age", min_value=0, max_value=120, value=25, step=1, key=f"{prefix}_age")
    with d2:
        gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"], key=f"{prefix}_gender")
    with d3:
        blood_group = st.selectbox(
            "Blood group",
            ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
            key=f"{prefix}_blood",
        )

    return {
        "patient_name": patient_name,
        "phone": phone,
        "age": age,
        "gender": gender,
        "blood_group": blood_group,
    }


def render_symptom_triage(user):
    st.markdown("""
    <div class="hero">
        <h1>🏥 CareConnect AI Pro</h1>
        <p>
            AI-Powered Rural Healthcare Assistant
            <br>
            Symptom Analysis • Prescription Reader • Hospital Locator • Appointment Booking
        </p>
    </div>
    """, unsafe_allow_html=True)

    disease_df, precaution_df = load_datasets()
    docs = build_documents(disease_df)
    embeddings = build_embeddings(docs)
    symptom_scores = build_symptom_scores(disease_df)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Symptom Triage Desk")
    st.caption("Use voice input or type symptoms separated by commas.")

    try:
        from streamlit_mic_recorder import speech_to_text
        voice_text = speech_to_text(
            language="en",
            start_prompt="Start voice input",
            stop_prompt="Stop recording",
            just_once=True,
            use_container_width=True,
            key="voice_symptoms",
        )
        
        if voice_text and voice_text.strip():
            st.session_state["symptom_text"] = voice_text
            st.toast("🎤 Voice captured successfully")
            
            # State evaluation deduplicator threshold filter
            if st.session_state.get("last_voice") != voice_text:
                st.session_state["last_voice"] = voice_text
                st.rerun()
            
    except Exception:
        st.caption("Voice input is optional. Install streamlit-mic-recorder to enable it.")

    if st.button("Reset symptom input"):
        st.session_state["symptom_text"] = ""
        st.rerun()

    symptom_text = st.text_area(
        "Symptoms",
        placeholder="Example: chest pain, fever",
        key="symptom_text",
        height=110,
    )

    patient = patient_demographics_form("triage", user)
    run = st.button("Run Advanced Triage", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not run:
        if st.session_state.get("last_assessment"):
            render_assessment_result(st.session_state["last_assessment"])
        return

    symptoms = parse_symptoms(symptom_text)
    if not symptoms:
        st.warning("Please enter at least one symptom.")
        return

    risk, score = calculate_risk(symptoms, symptom_scores, patient["age"])
    disease, context, confidence = retrieve_condition(symptoms, disease_df, docs, embeddings)
    precautions = get_precautions(precaution_df, disease)
    advice = get_ai_advice(symptoms=symptoms, disease=disease, risk=risk, context=context)

    record = {
        "patient_id": user["id"],
        "patient_name": patient["patient_name"] or user["name"],
        "phone": patient["phone"] or user.get("phone", ""),
        "age": patient["age"],
        "gender": patient["gender"],
        "blood_group": patient["blood_group"],
        "symptoms": ", ".join(symptoms),
        "disease": disease,
        "risk": risk,
        "score": score,
        "confidence": confidence,
        "context": context,
        "advice": advice,
        "precautions": "\n".join(precautions),
        "latitude": st.session_state.get("last_latitude"),
        "longitude": st.session_state.get("last_longitude"),
        "location_name": st.session_state.get("last_location_name", ""),
        "status": "New",
    }
    assessment_id = insert_record("assessments", record)
    record["id"] = assessment_id
    st.session_state["last_assessment"] = record
    st.success("Assessment saved.")
    render_assessment_result(record)


def render_assessment_result(record):
    st.markdown("### Clinical Assessment Result")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <p class="section-title">Urgency</p>
                {risk_badge(record["risk"])}
                <h2>{round(record["score"], 2)}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <p class="section-title">Predicted Condition</p>
                <h2>{record["disease"]}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <p class="section-title">Confidence</p>
                <h2>{record["confidence"]}%</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Dataset Evidence")
        st.write(record["context"])
        st.subheader("Precautions")
        for item in str(record["precautions"]).splitlines():
            st.write(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)

        special = recommend_specialist(record["disease"])

        st.subheader("Recommended Specialist")
        st.success(special)
        st.caption(
            "Based on the predicted condition, this specialist is the most suitable for consultation."
        )

        if "Cardiologist" in special:
            st.info("❤️ Recommended: Search nearby Cardiology Hospitals")
        elif "Neurologist" in special:
            st.info("🧠 Recommended: Search nearby Neurology Centers")
        elif "Dermatologist" in special:
            st.info("🩺 Recommended: Search nearby Skin Clinics")
        elif "Pulmonologist" in special:
            st.info("🫁 Recommended: Search nearby Respiratory Care Centers")
        else:
            st.info("🏥 Recommended: Visit the nearest General Hospital")

        cost_map = {
            "👨‍⚕️ General Physician": "₹300 - ₹600",
            "🧠 Neurologist": "₹800 - ₹2000",
            "❤️ Cardiologist": "₹700 - ₹1800",
            "🫁 Pulmonologist": "₹600 - ₹1500",
            "🩺 Dermatologist": "₹400 - ₹1200",
            "🩺 Gastroenterologist": "₹500 - ₹1500",
            "🩺 Urologist": "₹600 - ₹1500",
            "🩸 Endocrinologist": "₹700 - ₹1800",
            "🦟 Infectious Disease Specialist": "₹500 - ₹1400",
            "🩸 Hematologist": "₹700 - ₹1800",
        }

        st.info(
            f"Estimated Consultation Cost: "
            f"{cost_map.get(special, '₹300 - ₹1000')}"
        )

        st.subheader("AI Action Plan")
        st.write(record["advice"])

        st.markdown("</div>", unsafe_allow_html=True)

    if record["risk"] == "High Risk":
        st.error("🚨 Emergency warning: seek immediate professional medical care.")

        if st.button("🚨 EMERGENCY SOS", use_container_width=True):
            st.error(
                """
                SOS ALERT ACTIVATED
                
                📞 Call Ambulance: 108
                📞 Health Emergency: 102
                
                Proceed to the nearest hospital immediately.
                """
            )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                '<a href="tel:102" class="call-card"><strong>Call 102</strong><span>Ambulance service</span></a>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                '<a href="tel:108" class="call-card"><strong>Call 108</strong><span>Emergency medical response</span></a>',
                unsafe_allow_html=True,
            )
