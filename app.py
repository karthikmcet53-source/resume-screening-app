import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI

# ================== CONFIG ==================
st.set_page_config(page_title="AI Recruitment ATS", layout="wide")

# ================== UI STYLE ==================
st.markdown("""
<style>

/* MAIN BACKGROUND */
.stApp {
    background: #f1f5f9;
    color: #0f172a;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #020617;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0;
}

/* CARD */
.card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

/* BUTTON */
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}

/* INPUT */
textarea, input {
    background: white !important;
    color: black !important;
}

/* METRICS */
[data-testid="metric-container"] {
    background: white;
    padding: 15px;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# ================== INIT ==================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "df" not in st.session_state:
    st.session_state["df"] = None

if "decisions" not in st.session_state:
    st.session_state["decisions"] = {}

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
    match = re.findall(r'(\\d+)\\+?\\s+years', text.lower())
    return max([int(x) for x in match], default=0)


def ai_score(text, jd):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Score 0-100:\n{text[:1500]}\nJD:\n{jd[:800]}"}]
        )
        return float(res.choices[0].message.content.strip())
    except:
        return 50

# ================== HEADER ==================
st.markdown("""
<h1 style='text-align:center;'>🧠 AI Recruitment ATS</h1>
<p style='text-align:center;color:#475569;'>Smart Resume Screening Platform</p>
""", unsafe_allow_html=True)

# ================== SIDEBAR ==================
st.sidebar.title("🧠 ATS Panel")

page = st.sidebar.radio(
    "Navigation",
    ["📥 Screening", "📊 Dashboard", "📂 Pipeline"]
)

st.sidebar.markdown("---")

min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
min_exp = st.sidebar.slider("Minimum Experience", 0, 10, 0)

# ================== SCREENING ==================
if page == "📥 Screening":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload Resumes", type=["pdf","docx"], accept_multiple_files=True)
    jd = st.text_area("Paste Job Description")

    if st.button("🚀 Analyze Candidates"):

        if not uploaded_files or not jd:
            st.warning("Upload resumes and add job description")
        else:
            data = []

            for f in uploaded_files:
                text = extract_text(f)

                data.append({
                    "Candidate": f.name,
                    "Score": ai_score(text, jd),
                    "Experience": extract_experience(text)
                })

            df = pd.DataFrame(data)
            df = df[(df["Score"] >= min_score) & (df["Experience"] >= min_exp)]
            df = df.sort_values("Score", ascending=False)

            st.session_state["df"] = df

    st.markdown('</div>', unsafe_allow_html=True)

    # RESULTS
    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.subheader("🏆 Top Candidates")

        for i, row in df.head(5).iterrows():

            name = row["Candidate"]

            st.write(f"👤 {name}")
            st.write(f"Score: {row['Score']} | Experience: {row['Experience']}")

            col1, col2 = st.columns(2)

            if col1.button("Shortlist", key=f"s{i}"):
                st.session_state["decisions"][name] = "Shortlisted"

            if col2.button("Reject", key=f"r{i}"):
                st.session_state["decisions"][name] = "Rejected"

            decision = st.session_state["decisions"].get(name, "Pending")
            st.info(f"Status: {decision}")

            st.progress(int(row["Score"]))
            st.markdown("---")

        st.markdown('</div>', unsafe_allow_html=True)

# ================== DASHBOARD ==================
elif page == "📊 Dashboard":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Candidates", len(df))
        col2.metric("Avg Score", round(df["Score"].mean(), 2))
        col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

        st.bar_chart(df.set_index("Candidate")["Score"])

    else:
        st.info("Run screening first")

    st.markdown('</div>', unsafe_allow_html=True)

# ================== PIPELINE ==================
elif page == "📂 Pipeline":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state["df"] is not None:

        df = st.session_state["df"].copy()

        df["Decision"] = df["Candidate"].map(
            st.session_state["decisions"]
        ).fillna("Pending")

        st.dataframe(df, use_container_width=True)

    else:
        st.info("No candidates yet")

    st.markdown('</div>', unsafe_allow_html=True)
