import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import (
    dashboard_stats,
    doctor_queue,
    get_patient_records,
    search_records,
    table_df,
    update_record,
    insert_record,
)


def metric_card(label, value, caption=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="section-title">{label}</p>
            <h2>{value}</h2>
            <p class="section-copy">{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_patient_history(user, doctor_mode=False):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Patient Medical History")

    if doctor_mode or user["role"] in ["Doctor", "Admin"]:
        query = st.text_input("Search by patient name, phone, token, disease, or symptom")
        if query:
            assessments, appointments, prescriptions = search_records(query)
            st.markdown("#### Assessments")
            st.dataframe(assessments, use_container_width=True, hide_index=True)
            st.markdown("#### Appointments")
            st.dataframe(appointments, use_container_width=True, hide_index=True)
            st.markdown("#### Prescriptions")
            st.dataframe(prescriptions, use_container_width=True, hide_index=True)
        else:
            st.info("Enter a name, phone, token, disease, or symptom to search records.")
    else:
        assessments, appointments, reminders, followups, prescriptions = get_patient_records(user["id"])
        t1, t2, t3, t4, t5 = st.tabs(["Assessments", "Appointments", "Medicines", "Follow-ups", "Prescriptions"])
        with t1:
            st.dataframe(assessments, use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(appointments, use_container_width=True, hide_index=True)
        with t3:
            st.dataframe(reminders, use_container_width=True, hide_index=True)
        with t4:
            st.dataframe(followups, use_container_width=True, hide_index=True)
        with t5:
            st.dataframe(prescriptions, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_doctor_queue(user):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Doctor Queue Dashboard")
    st.caption("Medium and high-risk cases appear here for clinical review.")

    queue = doctor_queue()
    if queue.empty:
        st.info("No medium/high-risk cases in queue.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Upgrade 4: Dynamic Medical Queue Counters
    st.metric("🚨 Cases Waiting", len(queue))
    st.dataframe(queue, use_container_width=True, hide_index=True)
    
    st.markdown("### Update Case Status")
    ids = queue["id"].tolist()
    selected_id = st.selectbox("Assessment ID", ids)
    status = st.selectbox("Status", ["New", "Under Review", "Completed", "Referred"])
    note = st.text_area("Doctor note")

    if st.button("Update Case", use_container_width=True):
        update_record("assessments", selected_id, {"status": status, "doctor_note": note})
        st.success("Case updated.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_admin_dashboard(user, doctor_view=False):
    stats = dashboard_stats()
    assessments = stats["assessments"]
    appointments = stats["appointments"]
    prescriptions = stats["prescriptions"]
    users = stats["users"]
    feedback = stats["feedback"]

    st.markdown("## 📊 CareConnect AI Overview")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("👥 Users", len(users))
    with c2:
        st.metric("📋 Assessments", len(assessments))
    with c3:
        st.metric("📅 Appointments", len(appointments))
    with c4:
        st.metric("💊 Prescriptions", len(prescriptions))

    high_risk = (
        int((assessments["risk"] == "High Risk").sum())
        if not assessments.empty
        else 0
    )

    if high_risk > 0:
        st.error(f"🚨 {high_risk} High Risk Cases Need Immediate Review")
    else:
        st.success("✅ No High Risk Cases Pending")

    kpi_col1, kpi_col2 = st.columns(2)
    with kpi_col1:
        total_ai_usage = len(assessments) + len(prescriptions)
        st.metric("🤖 AI Usage", total_ai_usage)
    with kpi_col2:
        health_score = 100
        if high_risk > 0:
            health_score -= high_risk * 5
        health_score = max(health_score, 0)
        
        # Upgrade 2: Enterprise Diagnostic Vector Gauge Configuration
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=health_score,
                title={"text": "Community Health Score", "font": {"size": 16, "color": "#0f766e"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#0f766e"},
                    "bar": {"color": "#0f766e"},
                    "bgcolor": "white",
                    "borderwidth": 2,
                    "bordercolor": "#cbd5e1",
                    "steps": [
                        {"range": [0, 50], "color": "#fca5a5"},
                        {"range": [50, 80], "color": "#fde047"},
                        {"range": [80, 100], "color": "#ccfbf1"}
                    ],
                }
            )
        )
        fig_gauge.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Upgrade 1: Dynamic Structural Pipeline Feedback Analytics Engine
    if not feedback.empty:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("⭐ Feedback Analytics")
        
        # Clean down structural representation of metrics
        clean_feedback = feedback.copy()
        if clean_feedback["rating"].dtype == object:
            clean_feedback["rating"] = clean_feedback["rating"].str.count("⭐")
            
        rating_counts = clean_feedback["rating"].value_counts().sort_index().reset_index()
        rating_counts.columns = ["Rating", "Count"]
        
        fig_feedback = px.bar(
            rating_counts,
            x="Rating",
            y="Count",
            title="User Ratings Distribution",
            color="Count",
            color_continuous_scale="Teal"
        )
        fig_feedback.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1))
        st.plotly_chart(fig_feedback, use_container_width=True)
        st.markdown("</div><br>", unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Risk Distribution")
        if assessments.empty:
            st.info("No assessment data yet.")
        else:
            risk_counts = assessments["risk"].value_counts().reset_index()
            risk_counts.columns = ["Risk", "Count"]
            fig = px.pie(
                risk_counts,
                values="Count",
                names="Risk",
                hole=0.45,
                color_discrete_sequence=["#0f766e", "#d97706", "#dc2626"],
            )
            st.plotly_chart(fig, use_container_width=True)
            
        if not appointments.empty:
            st.markdown("---")
            st.subheader("Appointment Status")
            status_counts = appointments["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_appointments = px.bar(
                status_counts,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_sequence=["#0f766e", "#dc2626", "#2563eb"]
            )
            st.plotly_chart(fig_appointments, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with chart_col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Top Predicted Conditions")
        if assessments.empty:
            st.info("No disease trend data yet.")
        else:
            disease_counts = assessments["disease"].value_counts().head(8).reset_index()
            disease_counts.columns = ["Disease", "Count"]
            fig = px.bar(
                disease_counts,
                x="Count",
                y="Disease",
                orientation="h",
                color="Count",
                color_continuous_scale="Teal",
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Upgrade 3: Clinical Diagnostic Predictive Disease Multi-Line Metrics
            st.markdown("---")
            st.subheader("Disease Growth Projections")
            trend = assessments["disease"].value_counts().head(5).reset_index()
            trend.columns = ["Disease", "Cases"]
            
            fig_line = px.line(
                trend,
                x="Disease",
                y="Cases",
                markers=True,
                color_discrete_sequence=["#0891b2"]
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

    if not doctor_view:
        st.markdown("### Recent Data Log View")
        t1, t2, t3, t4 = st.tabs(["Assessments", "Appointments", "Prescriptions", "Feedback"])
        with t1:
            st.dataframe(assessments.head(25), use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(appointments.head(25), use_container_width=True, hide_index=True)
        with t3:
            st.dataframe(prescriptions.head(25), use_container_width=True, hide_index=True)
        with t4:
            st.dataframe(feedback.head(25), use_container_width=True, hide_index=True)


def render_health_tips():
    st.markdown("### Rural Health Tips")
    tips = [
        {
            "title": "Hydration and ORS",
            "body": "For diarrhea, vomiting, or heat exhaustion, use clean water and ORS. Seek care if weakness or low urine appears.",
        },
        {
            "title": "Emergency Warning Signs",
            "body": "Chest pain, breathing difficulty, unconsciousness, severe bleeding, stroke symptoms, and seizures need urgent care.",
        },
        {
            "title": "Medicine Safety",
            "body": "Do not take unknown tablets from old prescriptions. Confirm dosage with a doctor or pharmacist.",
        },
        {
            "title": "Fever Monitoring",
            "body": "Track temperature, hydration, rash, breathing, and energy level. Persistent high fever needs medical review.",
        },
        {
            "title": "Clinic Visit Preparation",
            "body": "Carry previous reports, medicine strips, allergies, and a written list of symptoms with start date.",
        },
        {
            "title": "Mosquito Protection",
            "body": "Use nets, avoid stagnant water, and seek testing for fever with chills or body pain.",
        },
    ]

    cols = st.columns(2)
    for idx, tip in enumerate(tips):
        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="panel">
                    <h3>{tip['title']}</h3>
                    <p>{tip['body']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_feedback(user, admin_mode=False):
    if admin_mode:
        st.markdown("### Feedback Management")
        feedback = table_df("feedback")
        st.dataframe(feedback, use_container_width=True, hide_index=True)
        if not feedback.empty:
            selected_id = st.selectbox("Feedback ID", feedback["id"].tolist())
            status = st.selectbox("Status", ["Open", "Reviewed", "Resolved"])
            if st.button("Update Feedback Status", use_container_width=True):
                update_record("feedback", selected_id, {"status": status})
                st.success("Feedback updated.")
        return

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Feedback")
    st.caption("Tell us what worked and what should improve.")

    # Upgrade 5: Premium Star Representation Selector Array Matrix
    rating_label = st.select_slider(
        "Rating",
        options=[
            "⭐",
            "⭐⭐",
            "⭐⭐⭐",
            "⭐⭐⭐⭐",
            "⭐⭐⭐⭐⭐"
        ],
        value="⭐⭐⭐⭐⭐"
    )
    
    category = st.selectbox(
        "Category",
        ["General", "Triage", "Prescription Reader", "Hospital Locator", "Appointments", "Reports"],
    )
    message = st.text_area("Message")

    if st.button("Submit Feedback", use_container_width=True):
        if not message.strip():
            st.warning("Please write a short message.")
        else:
            insert_record(
                "feedback",
                {
                    "user_id": user["id"],
                    "name": user["name"],
                    "role": user["role"],
                    "rating": rating_label,
                    "category": category,
                    "message": message,
                    "status": "Open",
                },
            )
            st.success("Thank you. Feedback submitted.")

    st.markdown("</div>", unsafe_allow_html=True)