import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI
from io import BytesIO

# ================== CONFIG ==================
st.set_page_config(page_title="AI Recruitment Dashboard", layout="wide")

# ================== LIGHT DASHBOARD UI ==================
st.markdown("""
<style>

/* MAIN BACKGROUND */
.stApp {
    background-color: #f5f7fb;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background-color: #1e293b;
}
[data-testid="stSidebar"] * {
    color: white;
}

/* CARDS */
.card {
    background: white;
    padding: 18px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 15px;
}

/* BUTTONS */
.stButton>button {
    background: #2563eb;
    color: white;
    border-radius: 8px;
    font-weight: 600;
}

/* METRICS */
[data-testid="metric-container"] {
    background: white;
    border-radius: 10px;
    padding: 12px;
}

/* TEXT AREA */
textarea {
    background: white !important;
    color: black !important;
}

/* HEADERS */
h1, h2, h3 {
    color: #1e293b;
}

</style>
""", unsafe_allow_html=True)

# ================== INIT ==================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "df" not in st.session_state:
    st.session_state.df = None

if "decisions" not in st.session_state:
    st.session_state.decisions = {}

if "resume_texts" not in st.session_state:
    st.session_state.resume_texts = {}

# ================== FUNCTIONS ==================

def extract_text(file):
    text = ""
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
    return text


def extract_experience(text):
    text = text.lower()
    patterns = [
        r'(\d+\.?\d*)\s*\+?\s*(years|yrs|year)',
        r'(\d+\.?\d*)\s*years?\s*of\s*experience',
        r'experience\s*[:\-]?\s*(\d+\.?\d*)'
    ]
    values = []
    for p in patterns:
        matches = re.findall(p, text)
        for m in matches:
            val = m[0] if isinstance(m, tuple) else m
            try:
                values.append(float(val))
            except:
                pass
    return max(values) if values else 0


def ai_score(text, jd):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Score resume 0-100:\n{text[:1500]}\n\nJD:\n{jd[:800]}"
            }]
        )
        return float(res.choices[0].message.content.strip())
    except:
        return 50


def convert_to_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    return output.getvalue()

# ================== HEADER ==================
st.title("📊 AI Recruitment Management Dashboard")
st.caption("Executive Hiring Decision Platform")

# ================== SIDEBAR ==================
page = st.sidebar.radio("Navigation", ["Screening", "Dashboard", "Pipeline"])

min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
min_exp = st.sidebar.slider("Minimum Experience", 0, 20, 0)

# ================== SCREENING ==================
if page == "Screening":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    files = st.file_uploader("Upload Resumes", ["pdf", "docx"], accept_multiple_files=True)
    jd = st.text_area("Paste Job Description")

    if st.button("🚀 Analyze Candidates"):

        if not files or not jd:
            st.warning("Upload resumes and add job description")
        else:
            rows = []

            with st.spinner("Analyzing resumes..."):
                for f in files:
                    text = extract_text(f)
                    st.session_state.resume_texts[f.name] = text

                    rows.append({
                        "Candidate": f.name,
                        "Score": ai_score(text, jd),
                        "Experience": extract_experience(text)
                    })

            df = pd.DataFrame(rows)

            df = df[
                (df["Score"] >= min_score) &
                (df["Experience"] >= min_exp)
            ].sort_values("Score", ascending=False)

            st.session_state.df = df
            st.success("Analysis Completed")

    st.markdown('</div>', unsafe_allow_html=True)

    # ================== RESULTS ==================
    if st.session_state.df is not None:

        df = st.session_state.df

        selected_candidate = st.selectbox(
            "Select Candidate for Preview",
            df["Candidate"]
        )

        col1, col2 = st.columns([1,2])

        # LEFT PANEL
        with col1:
            st.subheader("Candidates")

            for i, row in df.iterrows():

                name = row["Candidate"]
                key = f"{name}_{i}"

                st.markdown(f"**{name}**")
                st.write(f"Score: {row['Score']} | Exp: {row['Experience']}")

                if st.button("Shortlist", key=f"s_{key}"):
                    st.session_state.decisions[name] = "Shortlisted"
                    st.rerun()

                if st.button("Reject", key=f"r_{key}"):
                    st.session_state.decisions[name] = "Rejected"
                    st.rerun()

                status = st.session_state.decisions.get(name, "Pending")

                if status == "Shortlisted":
                    st.success("Shortlisted")
                elif status == "Rejected":
                    st.error("Rejected")
                else:
                    st.warning("Pending")

                st.markdown("---")

        # RIGHT PANEL (PREVIEW)
        with col2:
            st.subheader("📄 Resume Preview")

            text = st.session_state.resume_texts.get(selected_candidate, "")

            if text:
                st.text_area("Resume", text, height=500)
            else:
                st.info("No preview available")

# ================== DASHBOARD ==================
elif page == "Dashboard":

    if st.session_state.df is not None:

        df = st.session_state.df

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Candidates", len(df))
        col2.metric("Average Score", round(df["Score"].mean(), 2))
        col3.metric("Shortlisted",
            sum(1 for v in st.session_state.decisions.values() if v == "Shortlisted")
        )

        st.bar_chart(df.set_index("Candidate")["Score"])

    else:
        st.info("Run screening first")

# ================== PIPELINE ==================
elif page == "Pipeline":

    if st.session_state.df is not None:

        df = st.session_state.df.copy()

        df["Decision"] = df["Candidate"].map(
            st.session_state.decisions
        ).fillna("Pending")

        st.dataframe(df, use_container_width=True)

        excel = convert_to_excel(df)

        st.download_button(
            "📥 Export to Excel",
            excel,
            "ATS_Report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No data available")
