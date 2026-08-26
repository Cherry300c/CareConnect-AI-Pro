import io
import re
import time
import streamlit as st
from gtts import gTTS

from config import GEMINI_API_KEY, GEMINI_TEXT_MODELS, GEMINI_VISION_MODELS
from database import insert_record


@st.cache_resource
def get_ai_client():
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None


def _retry_delay_seconds(error):
    match = re.search(r"retry in ([0-9.]+)s", str(error), re.IGNORECASE)
    if not match:
        return None
    return min(float(match.group(1)) + 1, 25)


def friendly_ai_error(error):
    error_text = str(error).upper()
    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
        return (
            "Gemini has reached its current request limit. "
            "Please wait about a minute and try again. If this continues, "
            "check the Gemini API billing and quota for this project."
        )
    return "The AI service is temporarily unavailable. Please try again."


def generate_with_fallback(contents, models):
    client = get_ai_client()
    if client is None:
        raise RuntimeError("Gemini API key is not configured.")

    last_error = None
    for model_name in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                return response.text or ""
            except Exception as exc:
                last_error = exc
                error_text = str(exc).upper()
                retryable = [
                    "429", "500", "502", "503", "504",
                    "RESOURCE_EXHAUSTED", "UNAVAILABLE",
                ]
                if not any(code in error_text for code in retryable):
                    raise

                delay = _retry_delay_seconds(exc)
                if attempt == 0 and delay is not None:
                    time.sleep(delay)
                    continue
                break
    raise last_error


def static_health_advice(risk):
    if risk == "High Risk":
        return (
            "This case is high risk. Seek emergency medical care immediately. "
            "Keep the patient under observation and arrange transport to the nearest hospital."
        )
    if risk == "Medium Risk":
        return (
            "This case should be reviewed by a healthcare practitioner soon. "
            "Rest, hydrate, monitor symptoms, and book a clinic appointment."
        )
    return (
        "This appears low risk based on the entered symptoms. Rest, hydrate, "
        "and monitor symptoms. Seek care if symptoms worsen or persist."
    )


def get_ai_advice(symptoms, disease, risk, context):
    client = get_ai_client()
    if client is None:
        return static_health_advice(risk)

    prompt = f"""
You are CareConnect AI Pro.

Dataset context:
{context}

Patient symptoms:
{symptoms}

Predicted condition:
{disease}

Risk level:
{risk}

Create a simple, safe action plan:
1. What the patient should do now
2. Whether they should visit a doctor
3. What to monitor
4. What to avoid

Do not claim this is a final diagnosis.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text

    except Exception:
        return static_health_advice(risk)


def analyze_prescription_image(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        from google.genai import types

        image_part = types.Part.from_bytes(
            data=uploaded_file.getvalue(),
            mime_type=uploaded_file.type,
        )

        prompt = """
You are a clinical pharmacist assistant.

Analyze this prescription, medicine label, or medical report image.

Extract:
1. Medicine names
2. Dosage, if visible
3. Timing instructions, if visible
4. Patient-friendly explanation
5. Safety warnings for unclear handwriting or missing dosage.

Do not guess unreadable text.
"""

        return generate_with_fallback(
            contents=[image_part, prompt],
            models=GEMINI_VISION_MODELS,
        )

    except Exception as e:
        raise RuntimeError(friendly_ai_error(e)) from e


def render_prescription_reader(user):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Prescription Image Reader")
    st.caption("Upload a prescription, report, or medicine label.")

    patient_name = st.text_input(
        "Patient name",
        value=user.get("name", "") if user.get("role") == "Patient" else "",
        key="pres_patient_name",
    )
    phone = st.text_input(
        "Phone",
        value=user.get("phone", "") if user.get("role") == "Patient" else "",
        key="pres_phone",
    )
    uploaded_file = st.file_uploader(
        "Upload image",
        type=["png", "jpg", "jpeg", "webp"],
        key="pres_upload",
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded prescription", width=360)

    clicked = st.button("Analyze Prescription", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if clicked:
        if not uploaded_file:
            st.warning("Please upload an image first.")
            return

        with st.spinner("Reading prescription..."):
            try:
                result = analyze_prescription_image(uploaded_file)
            except Exception as error:
                st.error(str(error))
                return

        insert_record(
            "prescriptions",
            {
                "patient_id": user["id"],
                "patient_name": patient_name or user.get("name", ""),
                "phone": phone or user.get("phone", ""),
                "file_name": uploaded_file.name,
                "analysis": result,
            },
        )
        
        st.session_state["last_prescription_result"] = result
        st.success("Prescription analysis saved.")

    if st.session_state.get("last_prescription_result"):
        st.markdown("### Extracted Instructions")
        st.success("Prescription Analysis Completed")
        st.markdown(
            f"""
            <div class="panel">
            {st.session_state['last_prescription_result']}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_chatbot(user):
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("🤖 CareConnect AI Assistant")
    st.caption(
        "Ask health-related questions, get AI guidance, voice responses, and multilingual support."
    )
    st.caption(
        f"Chat History: {len(st.session_state.chat_history)//2} conversations"
    )

    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("🗑 Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.pop("last_chat_audio", None)
            st.session_state.pop("chat_audio_error", None)
            st.session_state["chat_question"] = ""
            st.rerun()
            
    with cc2:
        chat_text = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in st.session_state.chat_history
        )
        st.download_button(
            "📥 Download Chat",
            chat_text,
            file_name="careconnect_chat.txt",
            use_container_width=True
        )

    try:
        from streamlit_mic_recorder import speech_to_text

        voice_question = speech_to_text(
            language="en",
            start_prompt="🎤 Start Voice Question",
            stop_prompt="⏹ Stop Recording",
            just_once=True,
            use_container_width=True,
            key="chatbot_voice_input",
        )

        if voice_question and voice_question.strip():
            st.session_state["chat_question"] = voice_question
            st.toast("🎤 Voice captured successfully")
            
            # Deduplicated safe visual refresh wrapper
            if st.session_state.get("last_voice") != voice_question:
                st.session_state["last_voice"] = voice_question
                st.rerun()

    except Exception:
        pass

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.get("chat_history"):
        st.markdown("### 💬 Conversation")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if st.session_state.get("last_chat_audio"):
        st.audio(st.session_state["last_chat_audio"], format="audio/mp3")
    if st.session_state.get("chat_audio_error"):
        st.warning(st.session_state["chat_audio_error"])

    question = st.text_area(
        "Your question",
        key="chat_question",
        placeholder="Example: What should I do if fever continues for 2 days?",
        height=110,
    )

    if st.button("Ask CareConnect", use_container_width=True):
        if not question.strip():
            st.warning("Please type a question.")
        else:
            prompt = f"""
You are CareConnect AI Pro.
Answer this rural healthcare support question simply and safely.
Do not provide a final diagnosis.
User question: {question}
"""
            with st.spinner("🤖 CareConnect AI is analyzing..."):
                try:
                    answer = generate_with_fallback(prompt, GEMINI_TEXT_MODELS)
                except Exception as e:
                    answer = friendly_ai_error(e)
                    
            st.session_state.chat_history.append(
                {"role": "user", "content": question}
            )
            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )
            
            if "chat_question" in st.session_state:
                del st.session_state["chat_question"]

            try:
                audio_buffer = io.BytesIO()
                gTTS(text=answer, lang="en").write_to_fp(audio_buffer)
                st.session_state["last_chat_audio"] = audio_buffer.getvalue()
                st.session_state.pop("chat_audio_error", None)
            except Exception:
                st.session_state.pop("last_chat_audio", None)
                st.session_state["chat_audio_error"] = (
                    "The text answer was generated, but voice playback could "
                    "not be created. Check the internet connection and gTTS."
                )
            
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
