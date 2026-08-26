from datetime import datetime

import streamlit as st

from database import table_df


def clean_pdf_text(value):
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def split_text(text, max_len=85):
    text = clean_pdf_text(text)
    if not text.strip():
        return ["-"]
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_len:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["-"]


def report_text(record):
    return (
        "=== CARECONNECT AI PRO MEDICAL SUMMARY ===\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Token ID: {record.get('token_id', 'Not booked')}\n\n"
        "--- PATIENT ---\n"
        f"Name: {record.get('patient_name', '')}\n"
        f"Phone: {record.get('phone', '')}\n"
        f"Age: {record.get('age', '')}\n"
        f"Gender: {record.get('gender', '')}\n"
        f"Blood Group: {record.get('blood_group', '')}\n\n"
        "--- ASSESSMENT ---\n"
        f"Symptoms: {record.get('symptoms', '')}\n"
        f"Predicted Condition: {record.get('disease', '')}\n"
        f"Risk: {record.get('risk', '')}\n"
        f"Confidence: {record.get('confidence', '')}%\n\n"
        "--- APPOINTMENT ---\n"
        f"Facility: {record.get('facility', '')}\n"
        f"Address: {record.get('facility_address', '')}\n"
        f"Date: {record.get('appointment_date', '')}\n"
        f"Time: {record.get('appointment_time', '')}\n\n"
        "Important: This is a triage-support report, not a final diagnosis.\n"
    )


def report_html(record):
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>CareConnect AI Pro Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 32px;
                color: #0f172a;
                background: #f8fafc;
            }}
            h1 {{ color: #0f766e; }}
            .box {{
                background: white;
                border: 1px solid #dbe3ea;
                border-radius: 10px;
                padding: 16px;
                margin: 14px 0;
            }}
            .risk {{
                color: #dc2626;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>CareConnect AI Pro Medical Summary</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

        <div class="box">
            <h2>Patient</h2>
            <p><b>Name:</b> {record.get('patient_name', '')}</p>
            <p><b>Phone:</b> {record.get('phone', '')}</p>
            <p><b>Age:</b> {record.get('age', '')}</p>
            <p><b>Gender:</b> {record.get('gender', '')}</p>
            <p><b>Blood Group:</b> {record.get('blood_group', '')}</p>
        </div>

        <div class="box">
            <h2>Assessment</h2>
            <p><b>Symptoms:</b> {record.get('symptoms', '')}</p>
            <p><b>Predicted Condition:</b> {record.get('disease', '')}</p>
            <p><b>Risk:</b> <span class="risk">{record.get('risk', '')}</span></p>
            <p><b>Confidence:</b> {record.get('confidence', '')}%</p>
        </div>

        <div class="box">
            <h2>Appointment</h2>
            <p><b>Token:</b> {record.get('token_id', 'Not booked')}</p>
            <p><b>Facility:</b> {record.get('facility', '')}</p>
            <p><b>Address:</b> {record.get('facility_address', '')}</p>
            <p><b>Schedule:</b> {record.get('appointment_date', '')} at {record.get('appointment_time', '')}</p>
        </div>

        <p><i>This report supports healthcare navigation and triage. It is not a final medical diagnosis.</i></p>
    </body>
    </html>
    """


def report_pdf_bytes(record):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def title(text):
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, clean_pdf_text(text), ln=True)

    def section(text):
        pdf.ln(4)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, clean_pdf_text(text), ln=True)

    def field(label, value):
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, clean_pdf_text(label), ln=True)
        pdf.set_font("Arial", "", 10)
        for line in split_text(value):
            pdf.cell(0, 6, clean_pdf_text(line), ln=True)

    title("CareConnect AI Pro Medical Summary")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, clean_pdf_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)

    section("Patient")
    field("Name", record.get("patient_name", ""))
    field("Phone", record.get("phone", ""))
    field("Age", record.get("age", ""))
    field("Gender", record.get("gender", ""))
    field("Blood Group", record.get("blood_group", ""))

    section("Assessment")
    field("Symptoms", record.get("symptoms", ""))
    field("Predicted Condition", record.get("disease", ""))
    field("Risk", record.get("risk", ""))
    field("Confidence", f"{record.get('confidence', '')}%")

    section("Appointment")
    field("Token", record.get("token_id", "Not booked"))
    field("Facility", record.get("facility", ""))
    field("Address", record.get("facility_address", ""))
    field("Date", record.get("appointment_date", ""))
    field("Time", record.get("appointment_time", ""))

    section("Disclaimer")
    field("Note", "This report supports healthcare navigation and triage. It is not a final medical diagnosis.")

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)


def choose_report_record():
    booking = st.session_state.get("last_booking")
    assessment = st.session_state.get("last_assessment")

    if booking:
        record = dict(booking)
        if assessment:
            record["confidence"] = assessment.get("confidence", "")
        return record

    if assessment:
        return {
            "token_id": "Not booked",
            "patient_name": assessment.get("patient_name", ""),
            "phone": assessment.get("phone", ""),
            "age": assessment.get("age", ""),
            "gender": assessment.get("gender", ""),
            "blood_group": assessment.get("blood_group", ""),
            "symptoms": assessment.get("symptoms", ""),
            "disease": assessment.get("disease", ""),
            "risk": assessment.get("risk", ""),
            "confidence": assessment.get("confidence", ""),
            "facility": "",
            "facility_address": "",
            "appointment_date": "",
            "appointment_time": "",
        }

    return None


def render_report_center(user, admin_mode=False):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Report Center")
    st.caption("Generate text, HTML, and PDF reports.")

    record = choose_report_record()
    if record:
        st.success("A current report is ready.")
        st.download_button(
            "Download Text Report",
            data=report_text(record),
            file_name="CareConnect_Report.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.download_button(
            "Download HTML Report",
            data=report_html(record),
            file_name="CareConnect_Report.html",
            mime="text/html",
            use_container_width=True,
        )
        try:
            st.download_button(
                "Download PDF Report",
                data=report_pdf_bytes(record),
                file_name="CareConnect_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"PDF report could not be generated. Text and HTML reports are available. Details: {exc}")
    else:
        st.info("Run triage or book an appointment first to generate a report.")

    st.markdown("</div>", unsafe_allow_html=True)

    if admin_mode:
        st.markdown("### Data Exports")
        for table in [
            "users",
            "assessments",
            "appointments",
            "prescriptions",
            "medicine_reminders",
            "followups",
            "feedback",
        ]:
            df = table_df(table)
            st.download_button(
                f"Export {table}.csv",
                data=df.to_csv(index=False),
                file_name=f"{table}.csv",
                mime="text/csv",
                use_container_width=True,
            )
