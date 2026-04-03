import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI

# ================== CONFIG ==================
st.set_page_config(page_title="AI Recruitment ATS", layout="wide")

# ================== STYLE ==================
st.markdown("""
<style>
.stApp { background: #f1f5f9; }

.card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
}

.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 8px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ================== INIT ==================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "df" not in st.session_state:
    st.session_state.df = None

if "decisions" not in st.session_state:
    st.session_state.decisions = {}

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
        r'experience\s*[:\-]?\s*(\d+\.?\d*)',
        r'over\s*(\d+\.?\d*)\s*years',
        r'(\d+\.?\d*)\s*yr'
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            val = match[0] if isinstance(match, tuple) else match
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

# ================== HEADER ==================
st.title("🧠 AI Recruitment ATS")
st.caption("Smart Resume Screening System")

# ================== SIDEBAR ==================
st.sidebar.title("Navigation")

page = st.sidebar.radio("", ["Screening", "Dashboard", "Pipeline"])

st.sidebar.markdown("---")

min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
min_exp = st.sidebar.slider("Minimum Experience", 0, 20, 0)

st.sidebar.markdown("---")
st.sidebar.info("Upload resumes → Analyze → Shortlist or Reject")

# ================== SCREENING ==================
if page == "Screening":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    files = st.file_uploader("Upload Resumes", ["pdf", "docx"], accept_multiple_files=True)
    jd = st.text_area("Paste Job Description")

    if st.button("Analyze Candidates"):

        if not files or not jd:
            st.warning("Please upload resumes and enter job description")
        else:
            data = []

            with st.spinner("Analyzing resumes..."):
                for f in files:
                    text = extract_text(f)

                    data.append({
                        "Candidate": f.name,
                        "Score": ai_score(text, jd),
                        "Experience": extract_experience(text)
                    })

            df = pd.DataFrame(data)

            df = df[
                (df["Score"] >= min_score) &
                (df["Experience"] >= min_exp)
            ]

            df = df.sort_values("Score", ascending=False)

            st.session_state.df = df
            st.success("Analysis Complete!")

    st.markdown('</div>', unsafe_allow_html=True)

    # ================== RESULTS ==================
    if st.session_state.df is not None:

        df = st.session_state.df

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Top Candidates")

        for i, row in df.iterrows():

            name = row["Candidate"]
            key = f"{name}_{i}"

            st.markdown(f"### 👤 {name}")
            st.write(f"Score: {row['Score']} | Experience: {row['Experience']} yrs")

            col1, col2, col3 = st.columns([1,1,2])

            if col1.button("Shortlist", key=f"s_{key}"):
                st.session_state.decisions[name] = "Shortlisted"
                st.rerun()

            if col2.button("Reject", key=f"r_{key}"):
                st.session_state.decisions[name] = "Rejected"
                st.rerun()

            status = st.session_state.decisions.get(name, "Pending")

            if status == "Shortlisted":
                col3.success("Shortlisted")
            elif status == "Rejected":
                col3.error("Rejected")
            else:
                col3.warning("Pending")

            st.progress(int(row["Score"]))
            st.markdown("---")

        st.markdown('</div>', unsafe_allow_html=True)

# ================== DASHBOARD ==================
elif page == "Dashboard":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state.df is not None:

        df = st.session_state.df

        total = len(df)
        avg_score = round(df["Score"].mean(), 2)

        shortlisted = sum(
            1 for v in st.session_state.decisions.values()
            if v == "Shortlisted"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", total)
        col2.metric("Avg Score", avg_score)
        col3.metric("Shortlisted", shortlisted)

        st.bar_chart(df.set_index("Candidate")["Score"])

    else:
        st.info("Run screening first")

    st.markdown('</div>', unsafe_allow_html=True)

# ================== PIPELINE ==================
elif page == "Pipeline":

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state.df is not None:

        df = st.session_state.df.copy()

        df["Decision"] = df["Candidate"].map(
            st.session_state.decisions
        ).fillna("Pending")

        st.dataframe(df, use_container_width=True)

    else:
        st.info("No data available")

    st.markdown('</div>', unsafe_allow_html=True)
