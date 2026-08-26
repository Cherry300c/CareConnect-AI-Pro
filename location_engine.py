import math
import random
from datetime import date

import requests
import streamlit as st

from database import insert_record


def distance_km(lat1, lng1, lat2, lng2):
    radius = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def reverse_geocode(lat, lng):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 10, "addressdetails": 1},
            headers={"User-Agent": "CareConnectAIPro/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        address = response.json().get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
            or "Current Location"
        )
    except Exception:
        return "Current Location"


def osm_address(tags):
    if tags.get("addr:full"):
        return tags["addr:full"]
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village"),
    ]
    return ", ".join(part for part in parts if part) or tags.get("operator") or "Address not available"


def query_osm_facilities(lat, lng, care_level="clinic", radius_m=12000):
    amenity_filter = "^(hospital)$" if care_level == "emergency" else "^(hospital|clinic|doctors)$"
    query = (
        "[out:json][timeout:25];"
        "("
        f'node["amenity"~"{amenity_filter}"](around:{radius_m},{lat},{lng});'
        f'way["amenity"~"{amenity_filter}"](around:{radius_m},{lat},{lng});'
        f'relation["amenity"~"{amenity_filter}"](around:{radius_m},{lat},{lng});'
        f'node["healthcare"~"^(hospital|clinic|doctor)$"](around:{radius_m},{lat},{lng});'
        f'way["healthcare"~"^(hospital|clinic|doctor)$"](around:{radius_m},{lat},{lng});'
        f'relation["healthcare"~"^(hospital|clinic|doctor)$"](around:{radius_m},{lat},{lng});'
        ");"
        "out center tags;"
    )

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
    errors = []
    payload = None

    for endpoint in endpoints:
        try:
            response = requests.get(
                endpoint,
                params={"data": query},
                headers={"User-Agent": "CareConnectAIPro/1.0"},
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            errors.append(f"{endpoint}: {exc}")

    if payload is None:
        return [], "OpenStreetMap facility search failed. " + " | ".join(errors)

    facilities = []
    seen = set()
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("official_name")
        lat_value = element.get("lat") or element.get("center", {}).get("lat")
        lng_value = element.get("lon") or element.get("center", {}).get("lon")
        if not name or lat_value is None or lng_value is None:
            continue

        key = (name.lower(), round(lat_value, 5), round(lng_value, 5))
        if key in seen:
            continue
        seen.add(key)

        facilities.append(
            {
                "name": name,
                "address": osm_address(tags),
                "lat": lat_value,
                "lng": lng_value,
                "distance_km": distance_km(lat, lng, lat_value, lng_value),
                "source": "OpenStreetMap",
                "phone": tags.get("phone") or tags.get("contact:phone") or "",
                "website": tags.get("website") or tags.get("contact:website") or "",
            }
        )

    facilities.sort(key=lambda item: item["distance_km"])
    return facilities[:12], ""


def build_map(lat, lng, facilities, risk):
    import folium

    m = folium.Map(location=[lat, lng], zoom_start=13, tiles="CartoDB positron")
    folium.Marker(
        [lat, lng],
        popup="Your detected location",
        tooltip="Your location",
        icon=folium.Icon(color="blue", icon="home"),
    ).add_to(m)

    for facility in facilities:
        popup = (
            f"<b>{facility['name']}</b><br>"
            f"{facility['address']}<br>"
            f"Distance: {facility['distance_km']:.1f} km<br>"
            f"Source: {facility['source']}"
        )
        folium.Marker(
            [facility["lat"], facility["lng"]],
            popup=popup,
            tooltip=facility["name"],
            icon=folium.Icon(color="red" if risk == "High Risk" else "green", icon="plus-sign"),
        ).add_to(m)
    return m


def location_capture_panel():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Location Capture")
    st.caption("Use browser GPS or enter coordinates manually.")

    location = {}
    try:
        from streamlit_geolocation import streamlit_geolocation
        location = streamlit_geolocation()
    except Exception:
        st.caption("Browser geolocation component is optional. Manual entry is available.")

    gps_lat = location.get("latitude")
    gps_lng = location.get("longitude")

    c1, c2 = st.columns(2)
    with c1:
        manual_lat = st.number_input("Manual latitude", value=0.0, format="%.6f", key="manual_latitude")
    with c2:
        manual_lng = st.number_input("Manual longitude", value=0.0, format="%.6f", key="manual_longitude")

    lat = gps_lat or (manual_lat if manual_lat else None)
    lng = gps_lng or (manual_lng if manual_lng else None)

    if lat and lng:
        location_name = reverse_geocode(lat, lng)
        st.session_state["last_latitude"] = lat
        st.session_state["last_longitude"] = lng
        st.session_state["last_location_name"] = location_name
        st.success(f"Location ready: {location_name} ({lat:.4f}, {lng:.4f})")
    else:
        st.info("Waiting for location permission, or enter coordinates manually.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_hospital_locator(user):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Nearby Hospital & Clinic Locator")
    st.caption("Works without Google Maps key. Uses OpenStreetMap and Overpass.")
    st.markdown("</div>", unsafe_allow_html=True)

    location_capture_panel()
    lat = st.session_state.get("last_latitude")
    lng = st.session_state.get("last_longitude")
    if not lat or not lng:
        return

    assessment = st.session_state.get("last_assessment")
    risk = assessment["risk"] if assessment else "Medium Risk"
    care_level = "emergency" if risk == "High Risk" else "clinic"

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        search_clicked = st.button("Search Nearby Care Centers", use_container_width=True)
    with col2:
        radius = st.selectbox("Radius", [8000, 12000, 18000, 25000], index=1)

    if search_clicked:
        with st.spinner("Searching OpenStreetMap healthcare places..."):
            facilities, error = query_osm_facilities(lat, lng, care_level=care_level, radius_m=radius)
        st.session_state["nearby_facilities"] = facilities
        if error:
            st.warning(error)

    facilities = st.session_state.get("nearby_facilities", [])
    map_col, side_col = st.columns([1.25, 0.75], gap="large")

    with map_col:
        try:
            from streamlit_folium import st_folium
            m = build_map(lat, lng, facilities, risk)
            map_data = st_folium(m, width=760, height=500, key="care_map")
            clicked = map_data.get("last_object_clicked_tooltip") if map_data else None
            if clicked:
                st.session_state["selected_facility"] = clicked
        except Exception as exc:
            st.info(f"Map preview is unavailable, but search and booking still work. Details: {exc}")

    with side_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Nearest Care Options")
        if not facilities:
            st.info("Map shows your location. Click search to load nearby hospitals and clinics.")
        else:
            if not st.session_state.get("selected_facility"):
                st.session_state["selected_facility"] = facilities[0]["name"]
            for idx, facility in enumerate(facilities[:8], start=1):
                st.markdown(
                    f"""
                    <div class="mini-card">
                        <b>{idx}. {facility['name']}</b><br>
                        <span class="section-copy">{facility['address']}</span><br>
                        <span class="section-copy">{facility['distance_km']:.1f} km away - {facility['source']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    if facilities:
        render_appointment_booking(user, facilities, risk)


def render_appointment_booking(user, facilities, risk):
    st.markdown("### Appointment Booking")
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    facility_names = [f["name"] for f in facilities]
    selected_name = st.session_state.get("selected_facility") or facility_names[0]
    if selected_name not in facility_names:
        selected_name = facility_names[0]

    facility_name = st.selectbox("Selected facility", facility_names, index=facility_names.index(selected_name))
    facility = next(f for f in facilities if f["name"] == facility_name)

    patient_name = st.text_input(
        "Patient name",
        value=user["name"] if user["role"] == "Patient" else "",
        key="booking_patient_name",
    )
    phone = st.text_input(
        "Phone",
        value=user.get("phone", "") if user["role"] == "Patient" else "",
        key="booking_phone",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        age = st.number_input("Age", min_value=0, max_value=120, value=25, step=1, key="booking_age")
    with c2:
        gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"], key="booking_gender")
    with c3:
        blood_group = st.selectbox(
            "Blood group",
            ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
            key="booking_blood",
        )

    d1, d2 = st.columns(2)
    with d1:
        appointment_date = st.date_input("Date", value=date.today(), key="booking_date")
    with d2:
        appointment_time = st.selectbox(
            "Preferred slot",
            ["09:30 AM", "11:00 AM", "02:30 PM", "04:15 PM"],
            key="booking_time",
        )

    if st.button("Confirm Appointment Token", use_container_width=True):
        if not patient_name or not phone:
            st.error("Patient name and phone are required.")
        else:
            assessment = st.session_state.get("last_assessment", {})
            token_id = f"CC-PRO-{random.randint(10000, 99999)}"
            record = {
                "token_id": token_id,
                "patient_id": user["id"],
                "patient_name": patient_name,
                "phone": phone,
                "age": age,
                "gender": gender,
                "blood_group": blood_group,
                "facility": facility["name"],
                "facility_address": facility["address"],
                "appointment_date": str(appointment_date),
                "appointment_time": appointment_time,
                "disease": assessment.get("disease", ""),
                "risk": risk,
                "symptoms": assessment.get("symptoms", ""),
                "status": "Booked",
            }
            appointment_id = insert_record("appointments", record)
            record["id"] = appointment_id
            st.session_state["last_booking"] = record
            st.success(f"Appointment booked. Token ID: {token_id}")

    st.markdown("</div>", unsafe_allow_html=True)
