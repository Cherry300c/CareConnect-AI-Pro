from datetime import date, timedelta

import streamlit as st

from database import insert_record, table_df, update_record


def render_medicine_reminders(user):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Medicine Reminder Planner")
    st.caption("Create a simple medicine schedule for the patient.")

    medicine_name = st.text_input("Medicine name", key="med_name")
    dosage = st.text_input("Dosage", placeholder="Example: 1 tablet, 5 ml", key="med_dosage")
    timing = st.multiselect(
        "Timing",
        ["Morning", "Afternoon", "Evening", "Night", "Before food", "After food"],
        key="med_timing",
    )

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start date", value=date.today(), key="med_start")
    with c2:
        end_date = st.date_input("End date", value=date.today() + timedelta(days=5), key="med_end")

    notes = st.text_area(
        "Notes",
        placeholder="Example: Take after breakfast. Avoid skipping dose.",
        key="med_notes",
    )

    if st.button("Save Medicine Reminder", use_container_width=True):
        if not medicine_name:
            st.error("Medicine name is required.")
        elif end_date < start_date:
            st.error("End date cannot be before start date.")
        else:
            insert_record(
                "medicine_reminders",
                {
                    "patient_id": user["id"],
                    "medicine_name": medicine_name,
                    "dosage": dosage,
                    "timing": ", ".join(timing),
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "notes": notes,
                    "status": "Active",
                },
            )
            st.success("Medicine reminder saved.")

    st.markdown("</div>", unsafe_allow_html=True)

    reminders = table_df("medicine_reminders")
    if user["role"] == "Patient":
        reminders = reminders[reminders["patient_id"] == user["id"]]

    st.markdown("### Active Medicine Reminders")
    if reminders.empty:
        st.info("No reminders yet.")
    else:
        st.dataframe(reminders, use_container_width=True, hide_index=True)


def render_followups(user):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Follow-up Reminder")
    st.caption("Track review visits, lab report checks, and recovery monitoring.")

    title = st.text_input("Follow-up title", key="follow_title")
    followup_date = st.date_input("Follow-up date", value=date.today() + timedelta(days=7), key="follow_date")
    priority = st.selectbox("Priority", ["Low", "Medium", "High"], key="follow_priority")
    notes = st.text_area("Notes", key="follow_notes")

    if st.button("Save Follow-up", use_container_width=True):
        if not title:
            st.error("Follow-up title is required.")
        else:
            insert_record(
                "followups",
                {
                    "patient_id": user["id"],
                    "title": title,
                    "followup_date": str(followup_date),
                    "priority": priority,
                    "notes": notes,
                    "status": "Pending",
                },
            )
            st.success("Follow-up saved.")

    st.markdown("</div>", unsafe_allow_html=True)

    followups = table_df("followups")
    if user["role"] == "Patient":
        followups = followups[followups["patient_id"] == user["id"]]

    st.markdown("### Upcoming Follow-ups")
    if followups.empty:
        st.info("No follow-ups yet.")
    else:
        st.dataframe(followups, use_container_width=True, hide_index=True)


def render_reminder_admin():
    st.markdown("### Reminder Data")
    reminders = table_df("medicine_reminders")
    followups = table_df("followups")
    t1, t2 = st.tabs(["Medicine Reminders", "Follow-ups"])
    with t1:
        st.dataframe(reminders, use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(followups, use_container_width=True, hide_index=True)
