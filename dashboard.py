import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests

# Page Setup
st.set_page_config(
    page_title="CHRIST University - Smart Library Dashboard",
    layout="wide"
)

# Custom Sidebar CSS
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #1a1a2e;
}
[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #444;
}
[data-testid="stSidebar"] h3 {
    color: #f5c518 !important;
    font-size: 1rem;
}
[data-testid="stSidebar"] .stMultiSelect > div {
    background-color: #2a2a4a;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

# Load CSV Data
@st.cache_data
def load_data():
    df = pd.read_csv("christ_library_100_rows.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["hour"] = df["date"].dt.hour
    df["day"]  = df["date"].dt.strftime("%a")
    df["date_only"] = df["date"].dt.date
    return df

df = load_data()

# Fix fines — Rs. 5 per loan day for overdue books
df.loc[~df["returned"], "fine_rs"] = df.loc[~df["returned"], "loan_days"] * 5

DEPARTMENTS = sorted(df["department"].unique())
GENRES      = sorted(df["genre"].unique())

# Sidebar
with st.sidebar:
    st.image("christ_logo.jpg", width=110)
    st.markdown("### CHRIST University")
    st.markdown("**Central Library System**")
    st.markdown("---")

    st.markdown("#### Navigation")
    page = st.radio("", ["Home", "Book Catalog", "Overdue Management"],
                    label_visibility="collapsed")
    st.markdown("---")

    if page == "Home":
        st.markdown("#### Filters")
        sel_dept = st.multiselect(
            "Department", DEPARTMENTS, default=DEPARTMENTS,
            placeholder="Select departments..."
        )
        sel_genre = st.multiselect(
            "Genre", GENRES, default=GENRES,
            placeholder="Select genres..."
        )
        days_back = st.slider("Show last N days", 7, 90, 90)
        st.markdown("---")
        st.markdown("<small style='color:#aaa'>Filters apply to Home page only</small>",
                    unsafe_allow_html=True)
    else:
        sel_dept  = DEPARTMENTS
        sel_genre = GENRES
        days_back = 90

# Apply Filters
cutoff = datetime.today() - timedelta(days=days_back)
filt = df[
    df["department"].isin(sel_dept) &
    df["genre"].isin(sel_genre) &
    (df["date"] >= cutoff)
]

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: HOME
# ─────────────────────────────────────────────────────────────────────────────
if page == "Home":
    st.title("Smart Library Analytics Dashboard")
    st.caption("CHRIST (Deemed to be University) — Central Library")
    st.markdown("---")

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Borrows",   len(filt))
    col2.metric("Active Students", filt["student_id"].nunique())
    col3.metric("Overdue Books",   (~filt["returned"]).sum())
    col4.metric("Fines Collected", f"Rs. {filt['fine_rs'].sum():,}")

    st.markdown("---")

    # Row 1
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Borrows by Department")
        dept_data = filt["department"].value_counts().reset_index()
        dept_data.columns = ["Department", "Count"]
        fig = px.bar(dept_data, x="Count", y="Department", orientation="h",
                     color="Count", color_continuous_scale="Greens")
        fig.update_layout(coloraxis_showscale=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Genre Distribution")
        genre_data = filt["genre"].value_counts().reset_index()
        genre_data.columns = ["Genre", "Count"]
        fig = px.pie(genre_data, values="Count", names="Genre", hole=0.4)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Row 2 - full width
    st.subheader("Most Borrowed Genres")
    genre_bar = filt["genre"].value_counts().reset_index()
    genre_bar.columns = ["Genre", "Count"]
    fig = px.bar(genre_bar, x="Genre", y="Count",
                 color="Count", color_continuous_scale="Blues")
    fig.update_layout(height=320, coloraxis_showscale=False, xaxis_title="Genre")
    st.plotly_chart(fig, use_container_width=True)

    # Smart Alerts
    st.markdown("---")
    st.subheader("Smart Alerts")

    overdue_count = (~filt["returned"]).sum()
    busiest_day   = filt.groupby("day").size().idxmax()
    top_genre     = filt["genre"].value_counts().index[0]
    top_dept      = filt["department"].value_counts().index[0]
    total_fines   = filt["fine_rs"].sum()

    st.warning(f"{overdue_count} books are currently overdue. Reminder notifications recommended.")
    st.info(f"{busiest_day} is the busiest day of the week.")
    st.info(f"{top_dept} is the most active department.")
    st.success(f"{top_genre} is the most borrowed genre. Consider expanding this collection.")
    if total_fines > 0:
        st.warning(f"Rs. {total_fines:,} in pending fines.")

    st.markdown("---")
    st.caption("CHRIST (Deemed to be University) — Central Library System")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: BOOK CATALOG
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Book Catalog":
    st.title("Book Catalog")
    st.caption("Search real books using Open Library API")
    st.markdown("---")

    genre_counts   = df.groupby("genre").size()
    overdue_counts = df[~df["returned"]].groupby("genre").size()

    search_query = st.text_input(
        "Search by title, author or subject",
        placeholder="e.g. Python, Psychology, Law, Engineering"
    )

    if search_query:
        with st.spinner("Searching books..."):
            try:
                url      = f"https://openlibrary.org/search.json?q={search_query}&limit=12"
                response = requests.get(url, timeout=10)
                data     = response.json()
                books    = data.get("docs", [])

                if not books:
                    st.info("No books found. Try a different search term.")
                else:
                    st.markdown(f"Showing results for: **{search_query}**")
                    st.markdown("---")

                    for i in range(0, len(books), 3):
                        cols = st.columns(3)
                        for j, col in enumerate(cols):
                            if i + j < len(books):
                                book     = books[i + j]
                                title    = book.get("title", "Unknown Title")
                                author   = book.get("author_name", ["Unknown Author"])[0]
                                year     = book.get("first_publish_year", "N/A")
                                cover_id = book.get("cover_i")
                                subjects = book.get("subject", [])

                                matched_genre = None
                                for genre in GENRES:
                                    if any(genre.lower() in s.lower() for s in subjects):
                                        matched_genre = genre
                                        break

                                if matched_genre:
                                    borrowed = overdue_counts.get(matched_genre, 0)
                                    total    = genre_counts.get(matched_genre, 0)
                                    if borrowed == 0:
                                        availability = "Available"
                                        avail_color  = "green"
                                    elif borrowed < total:
                                        availability = "Limited Copies"
                                        avail_color  = "orange"
                                    else:
                                        availability = "All Copies Borrowed"
                                        avail_color  = "red"
                                else:
                                    availability = "Available"
                                    avail_color  = "green"

                                with col:
                                    if cover_id:
                                        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                                        st.image(cover_url, width=120)
                                    else:
                                        st.markdown("*(No cover available)*")

                                    st.markdown(f"**{title}**")
                                    st.markdown(f"Author: {author}")
                                    st.markdown(f"Year: {year}")
                                    st.markdown(f":{avail_color}[{availability}]")
                                    st.markdown("---")

            except requests.exceptions.ConnectionError:
                st.error("Could not connect to Open Library. Please check your internet connection.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
    else:
        st.info("Type a book title, author, or subject above to search.")
        st.markdown("---")
        st.subheader("Genre Summary in Our Library")
        genre_summary = df.groupby("genre").agg(
            Total_Borrowed=("genre", "count"),
            Currently_Overdue=("returned", lambda x: (~x).sum())
        ).reset_index()
        genre_summary.columns = ["Genre", "Total Borrowed", "Currently Overdue"]
        st.dataframe(genre_summary, use_container_width=True)

    st.markdown("---")
    st.caption("CHRIST (Deemed to be University) — Central Library System")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3: OVERDUE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Overdue Management":
    st.title("Overdue Management")
    st.caption("Track overdue books and pending fines")
    st.markdown("---")

    overdue_df = df[~df["returned"]].copy()

    sel_overdue_dept = st.multiselect(
        "Filter by Department", DEPARTMENTS, default=DEPARTMENTS
    )
    overdue_df = overdue_df[overdue_df["department"].isin(sel_overdue_dept)]

    st.markdown("---")

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Overdue",         len(overdue_df))
    col2.metric("Total Fines",           f"Rs. {overdue_df['fine_rs'].sum():,}")
    col3.metric("Students with Overdue", overdue_df["student_id"].nunique())
    col4.metric("Departments Affected",  overdue_df["department"].nunique())

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Overdue Books by Department")
        dept_overdue = overdue_df["department"].value_counts().reset_index()
        dept_overdue.columns = ["Department", "Overdue Count"]
        fig = px.bar(dept_overdue, x="Department", y="Overdue Count",
                     color="Overdue Count", color_continuous_scale="Reds")
        fig.update_layout(height=350, coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Total Fines by Department")
        dept_fines = overdue_df.groupby("department")["fine_rs"].sum().reset_index()
        dept_fines.columns = ["Department", "Total Fine (Rs.)"]
        dept_fines = dept_fines.sort_values("Total Fine (Rs.)", ascending=False)
        fig = px.bar(dept_fines, x="Department", y="Total Fine (Rs.)",
                     color="Total Fine (Rs.)", color_continuous_scale="Oranges")
        fig.update_layout(height=350, coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Overdue Records")

    display_df = overdue_df[
        ["student_id", "department", "genre", "floor", "loan_days", "fine_rs"]
    ].copy()
    display_df.columns = ["Student ID", "Department", "Genre", "Floor", "Loan Days", "Fine (Rs.)"]
    display_df = display_df.sort_values("Fine (Rs.)", ascending=False).reset_index(drop=True)

    st.dataframe(display_df, use_container_width=True, height=300)

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Overdue Records as CSV",
        data=csv,
        file_name="overdue_records.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.caption("CHRIST (Deemed to be University) — Central Library System")