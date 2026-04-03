import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI
from io import BytesIO   # ✅ NEW

# ================== CONFIG ==================
st.set_page_config(page_title="AI Recruitment ATS", layout="wide")

# ================== UI STYLE ==================
st.markdown("""
<style>
.stApp { background: #f1f5f9; color: #0f172a; }

[data-testid="stSidebar"] { background: #020617; }
[data-testid="stSidebar"] * { color: #e2e8f0; }

.card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}

textarea, input {
    background: white !important;
    color: black !important;
}

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

if "resume_texts" not in st.session_state:   # ✅ NEW
    st.session_state["resume_texts"] = {}

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
        r'experience\s*[:\-]?\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*years?\s*of\s*experience',
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
                continue

    return max(values) if values else 0


def ai_score(text, jd):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Score this resume from 0-100 based on JD:\n{text[:1500]}\n\nJD:\n{jd[:800]}"
            }]
        )
        return float(res.choices[0].message.content.strip())
    except:
        return 50


# ✅ NEW FUNCTION (EXPORT)
def convert_to_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    return output.getvalue()

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
min_exp = st.sidebar.slider("Minimum Experience", 0, 20, 0)

st.sidebar.markdown("---")

st.sidebar.subheader("📌 Instructions")
st.sidebar.markdown("""
1. Upload resumes  
2. Paste job description  
3. Click Analyze  
4. Review candidates  
5. Shortlist / Reject  
""")

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

                # ✅ STORE TEXT FOR PREVIEW
                st.session_state["resume_texts"][f.name] = text

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

            st.session_state["df"] = df

    st.markdown('</div>', unsafe_allow_html=True)

    # RESULTS + PREVIEW
    if st.session_state["df"] is not None:

        df = st.session_state["df"]

        # ✅ DROPDOWN FOR PREVIEW
        selected_candidate = st.selectbox(
            "🔍 Select Candidate for Resume Preview",
            df["Candidate"]
        )

        col_left, col_right = st.columns([1,2])

        # LEFT SIDE (UNCHANGED UI)
        with col_left:

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🏆 Top Candidates")

            for i, row in df.head(5).iterrows():

                name = row["Candidate"]

                st.write(f"👤 {name}")
                st.write(f"Score: {row['Score']} | Experience: {row['Experience']} yrs")

                col1, col2 = st.columns(2)

                if col1.button("✅ Shortlist", key=f"s{i}"):
                    st.session_state["decisions"][name] = "Shortlisted"

                if col2.button("❌ Reject", key=f"r{i}"):
                    st.session_state["decisions"][name] = "Rejected"

                decision = st.session_state["decisions"].get(name, "Pending")
                st.info(f"Status: {decision}")

                st.progress(int(row["Score"]))
                st.markdown("---")

            st.markdown('</div>', unsafe_allow_html=True)

        # RIGHT SIDE (✅ NEW PREVIEW)
        with col_right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📄 Resume Preview")

            text = st.session_state["resume_texts"].get(selected_candidate, "")

            if text:
                st.text_area("Resume Content", text, height=500)
            else:
                st.info("No preview available")

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

        # ✅ EXPORT BUTTON
        excel = convert_to_excel(df)

        st.download_button(
            label="📥 Export to Excel",
            data=excel,
            file_name="ATS_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No candidates yet")

    st.markdown('</div>', unsafe_allow_html=True)
