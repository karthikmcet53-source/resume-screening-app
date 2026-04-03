import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI

# ================== CONFIG ==================
st.set_page_config(page_title="AI Recruitment ATS", layout="wide")

# ================== CSS ==================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: white;
}
.glass {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# Sidebar style
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] {
    background: #020617;
}
[data-testid="stSidebar"] * {
    color: white;
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
    match = re.findall(r'(\d+)\+?\s+years', text.lower())
    return max([int(x) for x in match], default=0)


def ai_score(text, jd):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Score match 0-100:\n{text[:1500]}\nJD:\n{jd[:800]}"}]
        )
        return float(res.choices[0].message.content.strip())
    except:
        return 50


# ================== HEADER ==================
st.markdown("""
<h1 style='text-align:center;'>🧠 AI Recruitment ATS</h1>
<p style='text-align:center;color:#cbd5f5;'>Smart Resume Screening Platform</p>
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

# ================== PAGE 1 ==================
if page == "📥 Screening":

    st.markdown('<div class="glass">', unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload Resumes", type=["pdf","docx"], accept_multiple_files=True)
    jd = st.text_area("Paste Job Description")

    if st.button("🚀 Analyze"):

        if not uploaded_files or not jd:
            st.warning("Upload resumes & add JD")
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

    # SHOW RESULTS
    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        st.markdown('<div class="glass">', unsafe_allow_html=True)

        st.subheader("Top Candidates")

        for i, row in df.head(5).iterrows():

            c = row["Candidate"]

            st.markdown(f"**{c}** | Score: {row['Score']} | Exp: {row['Experience']}")

            col1, col2 = st.columns(2)

            if col1.button("Shortlist", key=f"s{i}"):
                st.session_state["decisions"][c] = "Shortlisted"

            if col2.button("Reject", key=f"r{i}"):
                st.session_state["decisions"][c] = "Rejected"

        st.markdown('</div>', unsafe_allow_html=True)

# ================== PAGE 2 ==================
elif page == "📊 Dashboard":

    st.markdown('<div class="glass">', unsafe_allow_html=True)

    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(df))
        col2.metric("Avg Score", round(df["Score"].mean(), 2))
        col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

        st.bar_chart(df.set_index("Candidate")["Score"])

    else:
        st.info("Run screening first")

    st.markdown('</div>', unsafe_allow_html=True)

# ================== PAGE 3 ==================
elif page == "📂 Pipeline":

    st.markdown('<div class="glass">', unsafe_allow_html=True)

    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        df["Decision"] = df["Candidate"].map(
            st.session_state["decisions"]
        ).fillna("Pending")

        st.dataframe(df)

    else:
        st.info("No data yet")

    st.markdown('</div>', unsafe_allow_html=True)
