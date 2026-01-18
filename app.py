import streamlit as st
import pandas as pd
import sqlite3
import pydeck as pdk

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Places Application",
    page_icon="📍",
    layout="wide"
)

# --------------------------------------------------
# CUSTOM CSS – UI / UX
# --------------------------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 2.8rem !important;
}

h1 {
    margin-top: 0.4rem !important;
    padding-top: 0 !important;
}

body {
    background-color:#f2f2f2 !important;
}

.place-card {
    background:#f3f3f3;
    padding:16px;
    border-radius:14px;
    border:1px solid #dcdcdc;
    margin-bottom:12px;
    transition:0.2s ease;
}
.place-card:hover {
    background:#e9e9e9;
    border-color:#bfbfbf;
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
        "rating": rating,
    }

    if "owner_id" in info["name"].values:
        col = info[info["name"] == "owner_id"].iloc[0]
        if col["notnull"] == 1 and col["dflt_value"] is None:
            values["owner_id"] = 1

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
    search = st.text_input(
        "🔍 Search by name",
        placeholder="Cauta locatia dupa nume..."
    )

with f3:
    sort_by = st.selectbox("Sort by", ["Rating ↓", "Rating ↑", "Name A-Z"])

# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------
filtered = df.copy()

if search:
    filtered = filtered[
        filtered["name"].str.contains(search, case=False, na=False)
    ]

filtered = filtered[filtered["rating"] >= min_rating]

if sort_by == "Rating ↓":
    filtered = filtered.sort_values("rating", ascending=False)
elif sort_by == "Rating ↑":
    filtered = filtered.sort_values("rating", ascending=True)
else:
    filtered = filtered.sort_values("name")

st.divider()

# --------------------------------------------------
# MAIN LAYOUT
# --------------------------------------------------
left, right = st.columns([1, 1.4])

# --------------------------------------------------
# LEFT – SAVED LOCATIONS (SCROLL)
# --------------------------------------------------
with left:
    st.subheader("📌 Saved locations")

    if filtered.empty:
        st.info("Nu există locații.")
    else:
        with st.container(height=460):   # ♻️ SCROLL REAL, FIX, EXACT CAT HARTA
            for idx, row in filtered.iterrows():
                key = f"{row['rowid']}_{idx}"

                st.markdown(
                    f"""
                    <div class="place-card">
                        <b>{row['name']}</b><br>
                        <small>{row['city']}</small><br>
                        ⭐ Rating: <b>{row['rating']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                c1, c2, c3 = st.columns([1, 1, 2])

                if c1.button("🗑️ Delete", key=f"del_{key}"):
                    delete_place(row["rowid"])
                    st.rerun()

                if c2.button("✏️ Edit", key=f"edit_{key}"):
                    st.session_state["edit_id"] = row["rowid"]

                if c3.button("📍 Show on map", key=f"map_{key}"):
                    st.session_state["map_lat"] = row["lat"]
                    st.session_state["map_lng"] = row["lng"]
                    st.session_state["zoom"] = 13
                    st.rerun()

# --------------------------------------------------
# RIGHT – MAP
# --------------------------------------------------
with right:
    st.subheader("🗺️ Map")

    if not filtered.empty:
        PIN_URL = "https://cdn-icons-png.flaticon.com/512/684/684908.png"

        filtered = filtered.copy()
        filtered["icon_data"] = filtered["rating"].apply(
            lambda _: {
                "url": PIN_URL,
                "width": 512,
                "height": 512,
                "anchorY": 512
            }
        )

        lat_c = st.session_state.get("map_lat", filtered.iloc[0]["lat"])
        lng_c = st.session_state.get("map_lng", filtered.iloc[0]["lng"])
        zoom_c = st.session_state.get("zoom", 10)

        layer = pdk.Layer(
            "IconLayer",
            data=filtered,
            get_position="[lng, lat]",
            get_icon="icon_data",
            get_size=5,
            size_scale=10,
            pickable=True
        )

        view = pdk.ViewState(
            latitude=lat_c,
            longitude=lng_c,
            zoom=zoom_c
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text": "{name}\n⭐ {rating}"}
            ),
            height=460
        )
    else:
        st.info("Harta va apărea după adăugare.")

st.divider()

# --------------------------------------------------
# ADD NEW PLACE
# --------------------------------------------------
st.subheader("➕ Add new place")

with st.form("add_place"):
    c1, c2 = st.columns(2)

    with c1:
        name = st.text_input("📌 Name")
        city = st.text_input("🏙️ City")

    with c2:
        lat = st.number_input("🌍 Latitude", format="%.6f")
        lng = st.number_input("🌍 Longitude", format="%.6f")

    rating = st.slider("⭐ Rating", 0.0, 5.0, 3.0)

    if st.form_submit_button("Add place"):
        if not name or not city:
            st.error("Name și City sunt obligatorii.")
        else:
            add_place(name, city, lat, lng, rating)
            st.success("Locație adăugată!")
            st.rerun()

# --------------------------------------------------
# EDIT PLACE
# --------------------------------------------------
if "edit_id" in st.session_state:
    row = df[df["rowid"] == st.session_state["edit_id"]].iloc[0]

    st.divider()
    st.subheader("✏️ Edit location")

    with st.form("edit_form"):
        name_e = st.text_input("Name", row["name"])
        city_e = st.text_input("City", row["city"])
        lat_e = st.number_input("Latitude", value=row["lat"], format="%.6f")
        lng_e = st.number_input("Longitude", value=row["lng"], format="%.6f")
        rating_e = st.slider("Rating", 0.0, 5.0, row["rating"])

        b1, b2 = st.columns(2)

        if b1.form_submit_button("Save"):
            update_place(row["rowid"], name_e, city_e, lat_e, lng_e, rating_e)
            del st.session_state["edit_id"]
            st.rerun()

        if b2.form_submit_button("Cancel"):
            del st.session_state["edit_id"]
            st.rerun()

# --------------------------------------------------
# STATISTICS SECTION (placeholder for your colleague)
# --------------------------------------------------
st.divider()
st.subheader("📊 Statistics & Visualizations")

st.info("Aici vor fi integrate graficele și statisticile")
