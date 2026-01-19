import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Places Application",
    page_icon="📍",
    layout="wide"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------
st.markdown("""
<style>
.block-container { padding-top: 2.5rem; }
body { background:#f2f2f2; }
.place-card {
    background:#f3f3f3;
    padding:14px;
    border-radius:14px;
    border:1px solid #dcdcdc;
    margin-bottom:10px;
}
.place-card:hover {
    background:#e9e9e9;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("📍 Places Application")
st.caption("Salvează, editează și vizualizează locații preferate")
st.divider()

# --------------------------------------------------
# DB CONNECTION
# --------------------------------------------------
conn = sqlite3.connect("data/places.sqlite", check_same_thread=False)

def get_places():
    return pd.read_sql("SELECT rowid, * FROM places", conn)

def add_place(name, city, lat, lng, rating):
    info = pd.read_sql("PRAGMA table_info(places);", conn)

    values = {
        "name": name,
        "city": city,
        "lat": lat,
        "lng": lng,
        "rating": rating
    }

    # rezolva owner_id NOT NULL
    if "owner_id" in info["name"].values:
        col = info[info["name"] == "owner_id"].iloc[0]
        if col["notnull"] == 1:
            values["owner_id"] = 1

    # completeaza coloane suplimentare cu NULL
    for col in info["name"]:
        if col not in values and col.lower() != "rowid":
            values[col] = None

    columns = ", ".join(values.keys())
    placeholders = ", ".join(["?"] * len(values))
    sql = f"INSERT INTO places ({columns}) VALUES ({placeholders})"

    conn.execute(sql, tuple(values.values()))
    conn.commit()

def delete_place(rowid):
    conn.execute("DELETE FROM places WHERE rowid=?", (rowid,))
    conn.commit()

def update_place(rowid, name, city, lat, lng, rating):
    conn.execute("""
        UPDATE places
        SET name=?, city=?, lat=?, lng=?, rating=?
        WHERE rowid=?
    """, (name, city, lat, lng, rating, rowid))
    conn.commit()

df = get_places()

# --------------------------------------------------
# FILTERS
# --------------------------------------------------
st.subheader("🎛️ Filters")

f1, f2, f3 = st.columns([1.2, 1.8, 1])

with f1:
    min_rating = st.slider("⭐ Min rating", 0.0, 5.0, 0.0)

with f2:
    search = st.text_input("🔍 Search by name")

with f3:
    sort_by = st.selectbox("Sort by", ["Rating ↓", "Rating ↑", "Name A-Z"])

filtered = df.copy()

if search:
    filtered = filtered[filtered["name"].str.contains(search, case=False, na=False)]

filtered = filtered[filtered["rating"] >= min_rating]

if sort_by == "Rating ↓":
    filtered = filtered.sort_values("rating", ascending=False)
elif sort_by == "Rating ↑":
    filtered = filtered.sort_values("rating")
else:
    filtered = filtered.sort_values("name")

st.divider()

# --------------------------------------------------
# LAYOUT
# --------------------------------------------------
left, right = st.columns([1.6, 2.1])

# --------------------------------------------------
# LEFT – LIST
# --------------------------------------------------
with left:
    st.subheader("📌 Saved locations")

    if filtered.empty:
        st.info("Nu există locații.")
    else:
        with st.container(height=680):
            for i, r in filtered.iterrows():
                key = f"{r.rowid}_{i}"

                st.markdown(f"""
                <div class="place-card">
                    <b>{r['name']}</b><br>
                    <small>{r['city']}</small><br>
                    ⭐ <b>{r['rating']}</b>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)

                if c1.button("🗑️", key=f"del_{key}"):
                    delete_place(r.rowid)
                    st.rerun()

                if c2.button("✏️", key=f"edit_{key}"):
                    st.session_state["edit_id"] = r.rowid

                if c3.button("📍", key=f"map_{key}"):
                    st.session_state["map_lat"] = r.lat
                    st.session_state["map_lng"] = r.lng
                    st.session_state["zoom"] = 15
                    st.rerun()

# --------------------------------------------------
# RIGHT – MAP (CLICK → ADD)
# --------------------------------------------------
with right:
    st.subheader("🗺️ Map (click pe hartă pentru a adăuga)")
    # extinde harta pe toata latimea coloanei
    st.markdown(
        "<style>.folium-map{width:100% !important;}</style>",
        unsafe_allow_html=True
    )

    center = [
        st.session_state.get("map_lat", 44.4268),
        st.session_state.get("map_lng", 26.1025)
    ]
    zoom = st.session_state.get("zoom", 12)

    m = folium.Map(location=center, zoom_start=zoom)

    # markers existente
    for _, r in df.iterrows():
        folium.Marker(
            [r.lat, r.lng],
            popup=f"<b>{r['name']}</b><br>{r['city']}<br>⭐ {r['rating']}",
            tooltip=r["name"]
        ).add_to(m)

    result = st_folium(
    m,
    height=680,   # înălțime mărită
    width="100%", # folosește toată coloana
    returned_objects=["last_clicked"]
)



    if result and result.get("last_clicked"):
        lat = result["last_clicked"]["lat"]
        lng = result["last_clicked"]["lng"]

        st.success(f"Locatie selectata: {lat:.6f}, {lng:.6f}")

        with st.form("add_from_map"):
            st.write("### ➕ Add new place")

            name = st.text_input("📌 Name")
            city = st.text_input("🏙️ City")
            rating = st.slider("⭐ Rating", 0.0, 5.0, 3.0)

            if st.form_submit_button("Save"):
                add_place(name, city, lat, lng, rating)
                st.rerun()

# --------------------------------------------------
# EDIT
# --------------------------------------------------
if "edit_id" in st.session_state:
    row = df[df.rowid == st.session_state["edit_id"]].iloc[0]

    st.divider()
    st.subheader("✏️ Edit location")

    with st.form("edit_form"):
        name = st.text_input("Name", row.name)
        city = st.text_input("City", row.city)
        lat = st.number_input("Latitude", value=row.lat, format="%.6f")
        lng = st.number_input("Longitude", value=row.lng, format="%.6f")
        rating = st.slider("Rating", 0.0, 5.0, float(row.rating))

        c1, c2 = st.columns(2)
        if c1.form_submit_button("Save"):
            update_place(row.rowid, name, city, lat, lng, rating)
            del st.session_state["edit_id"]
            st.rerun()

        if c2.form_submit_button("Cancel"):
            del st.session_state["edit_id"]
            st.rerun()

# --------------------------------------------------
# STATS PLACEHOLDER
# --------------------------------------------------
st.divider()
st.subheader("📊 Statistics & Visualizations")
st.info("Aici vor fi integrate graficele și statisticile.")
