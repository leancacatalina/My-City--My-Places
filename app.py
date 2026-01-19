import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
import altair as alt

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
.place-card:hover { background:#e9e9e9; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("📍 Places Application")
st.caption("Salveaza, editeaza si vizualizeaza locatii preferate")
st.divider()

# --------------------------------------------------
# DB CONNECTION
# --------------------------------------------------
conn = sqlite3.connect("data/places.sqlite", check_same_thread=False)

def get_places():
    return pd.read_sql("SELECT rowid, * FROM places", conn)


# ----------- ADD PLACE (EXTINS cu câmpurile colegei) ----------------
def add_place(name, city, lat, lng, rating, is_shared_with_family=False, family_id=None, category=None):
    info = pd.read_sql("PRAGMA table_info(places)", conn)
    cols = set(info["name"])

    values = {
        "name": name,
        "city": city,
        "lat": lat,
        "lng": lng,
        "rating": rating
    }

    if "owner_id" in cols:
        values["owner_id"] = "user_001"

    if "is_shared_with_family" in cols:
        values["is_shared_with_family"] = 1 if is_shared_with_family else 0

    if "family_id" in cols:
        values["family_id"] = family_id if is_shared_with_family else None

    if "category" in cols:
        values["category"] = category

    for col in cols:
        if col not in values and col.lower() != "rowid":
            values[col] = None

    sql = f"INSERT INTO places ({', '.join(values.keys())}) VALUES ({', '.join(['?'] * len(values))})"
    conn.execute(sql, tuple(values.values()))
    conn.commit()


# ----------- UPDATE PLACE ----------------
def update_place(rowid, name, city, lat, lng, rating, is_shared_with_family=False, family_id=None, category=None):
    info = pd.read_sql("PRAGMA table_info(places)", conn)
    cols = set(info["name"])

    sets = ["name=?", "city=?", "lat=?", "lng=?", "rating=?"]
    vals = [name, city, lat, lng, rating]

    if "is_shared_with_family" in cols:
        sets.append("is_shared_with_family=?")
        vals.append(1 if is_shared_with_family else 0)

    if "family_id" in cols:
        sets.append("family_id=?")
        vals.append(family_id)

    if "category" in cols:
        sets.append("category=?")
        vals.append(category)

    vals.append(rowid)
    conn.execute(f"UPDATE places SET {', '.join(sets)} WHERE rowid=?", vals)
    conn.commit()


def delete_place(rowid):
    conn.execute("DELETE FROM places WHERE rowid=?", (rowid,))
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
        st.info("Nu exista locatii.")
    else:
        with st.container(height=680):
            for i, r in filtered.iterrows():
                key = f"{r.rowid}_{i}"

                st.markdown(f"""
                <div class="place-card">
                    <b>{r['name']}</b><br>
                    <small>{r['city']}</small><br>
                    ⭐ <b>{r['rating']}</b><br>
                    🏷️ {r.get('category', '—')}
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
# RIGHT – MAP
# --------------------------------------------------
with right:
    st.subheader("🗺️ Map (click pe harta pentru a adauga)")

    st.markdown("<style>.folium-map{width:100% !important;}</style>", unsafe_allow_html=True)

    center = [
        st.session_state.get("map_lat", 44.4268),
        st.session_state.get("map_lng", 26.1025)
    ]
    zoom = st.session_state.get("zoom", 12)

    m = folium.Map(location=center, zoom_start=zoom)

    # existing markers
    for _, r in df.iterrows():
        folium.Marker(
            [r.lat, r.lng],
            popup=f"<b>{r['name']}</b><br>{r['city']}<br>⭐ {r['rating']}",
            tooltip=r["name"]
        ).add_to(m)

    result = st_folium(m, height=680, width="100%", returned_objects=["last_clicked"])

    if result and result.get("last_clicked"):
        lat = result["last_clicked"]["lat"]
        lng = result["last_clicked"]["lng"]

        st.success(f"Locatie selectata: {lat:.6f}, {lng:.6f}")

        with st.form("add_from_map"):
            st.write("### ➕ Add new place")
            name = st.text_input("📌 Name")
            city = st.text_input("🏙️ City")
            rating = st.slider("⭐ Rating", 0.0, 5.0, 3.0)
            share = st.checkbox("👨‍👩‍👧‍👦 Shared with family")
            family_id = st.text_input("Family ID")
            category = st.selectbox("🏷️ Category", ["coffee", "restaurant", "park", "museum", "gym", "shop", "library", "other"])

            if st.form_submit_button("Save"):
                add_place(name, city, lat, lng, rating, share, family_id, category)
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
        share = st.checkbox("Shared with family", value=bool(row.get("is_shared_with_family", 0)))
        family_id = st.text_input("Family ID", value=row.get("family_id") or "")
        category = st.selectbox(
            "🏷️ Category",
            ["coffee", "restaurant", "park", "museum", "gym", "shop", "library", "other"],
            index=["coffee","restaurant","park","museum","gym","shop","library","other"].index(row.get("category") or "other")
        )

        c1, c2 = st.columns(2)

        if c1.form_submit_button("Save"):
            update_place(row.rowid, name, city, lat, lng, rating, share, family_id, category)
            del st.session_state["edit_id"]
            st.rerun()

        if c2.form_submit_button("Cancel"):
            del st.session_state["edit_id"]
            st.rerun()

# --------------------------------------------------
# STATISTICS SECTION — COMPLET
# --------------------------------------------------
st.divider()
st.subheader("📊 Statistics & Visualizations")

df_stats = filtered.copy()

if df_stats.empty:
    st.info("Nu exista date pentru statistici.")
else:
    total = len(df_stats)
    avg_rating = df_stats["rating"].dropna().mean()
    shared_pct = (df_stats["is_shared_with_family"].fillna(0).astype(int).mean()) * 100
    n_cats = df_stats["category"].fillna("unknown").nunique()
    n_cities = df_stats["city"].fillna("unknown").nunique()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total places", total)
    k2.metric("Avg rating", f"{avg_rating:.2f}")
    k3.metric("Shared w/ family", f"{shared_pct:.1f}%")
    k4.metric("Categories", n_cats)
    k5.metric("Cities", n_cities)

    st.divider()

    # CATEGORY CHART
    cat_counts = (
        df_stats.assign(category=df_stats["category"].fillna("unknown"))
                .groupby("category", as_index=False)
                .size()
                .rename(columns={"size": "count"})
                .sort_values("count", ascending=False)
    )

    ch1 = alt.Chart(cat_counts).mark_bar().encode(
        x="category:N",
        y="count:Q",
        tooltip=["category", "count"]
    ).properties(height=260, title="Places by category")

    st.altair_chart(ch1, width="stretch")

    # RATING CHART
    df_r = df_stats[df_stats["rating"].notna()].copy()
    df_r["rating_star"] = df_r["rating"].round().clip(1, 5).astype(int)

    rating_counts = (
        df_r.groupby("rating_star", as_index=False)
            .size()
            .rename(columns={"size": "count"})
    )

    # include ratings with zero count
    all_ratings = pd.DataFrame({"rating_star": [1,2,3,4,5]})
    rating_counts = all_ratings.merge(rating_counts, on="rating_star", how="left").fillna({"count":0})
    rating_counts["count"] = rating_counts["count"].astype(int)
    rating_counts["stars"] = rating_counts["rating_star"].apply(lambda x: "⭐" * x)

    ch2 = alt.Chart(rating_counts).mark_bar().encode(
        x=alt.X("stars:N", sort=["⭐⭐⭐⭐⭐","⭐⭐⭐⭐","⭐⭐⭐","⭐⭐","⭐"]),
        y="count:Q",
        tooltip=["rating_star", "count"]
    ).properties(height=260, title="Rating distribution")

    st.altair_chart(ch2, width="stretch")

    # CITY CHART
    city_counts = (
        df_stats.assign(city=df_stats["city"].fillna("unknown"))
                .groupby("city", as_index=False)
                .size()
                .rename(columns={"size": "count"})
                .sort_values("count", ascending=False)
    )

    ch4 = alt.Chart(city_counts).mark_bar().encode(
        x="city:N",
        y="count:Q",
        tooltip=["city", "count"]
    ).properties(height=260, title="Places by city")

    st.altair_chart(ch4, width="stretch")

    # SHARED VS PRIVATE
    shared_counts = pd.DataFrame({
        "type": ["Private", "Family-shared"],
        "count": [
            int((df_stats["is_shared_with_family"].fillna(0)==0).sum()),
            int((df_stats["is_shared_with_family"].fillna(0)==1).sum())
        ]
    })

    ch3 = alt.Chart(shared_counts).mark_bar().encode(
        x="type:N",
        y="count:Q",
        tooltip=["type", "count"]
    ).properties(height=260, title="Private vs Family-shared")

    st.altair_chart(ch3, width="stretch")
