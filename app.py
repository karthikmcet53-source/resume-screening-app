import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI

# ================= INIT =================
st.set_page_config(page_title="AI Recruitment ATS", layout="wide")
st.markdown("""
<style>

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: white;
}

/* Glass Card */
.glass {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 10px;
    padding: 10px 20px;
    border: none;
    font-weight: 600;
    transition: 0.3s;
}

.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 20px rgba(99,102,241,0.5);
}

/* Tabs */
button[data-baseweb="tab"] {
    font-size: 16px;
    font-weight: 600;
    color: #cbd5f5;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: white;
    border-bottom: 3px solid #6366f1;
}

/* Metrics */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.08);
    padding: 15px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Input fields */
textarea, input {
    background-color: rgba(255,255,255,0.08) !important;
    color: white !important;
}

/* Progress bar */
.stProgress > div > div > div {
    background-color: #6366f1;
}

</style>
""", unsafe_allow_html=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "decisions" not in st.session_state:
    st.session_state["decisions"] = {}

# ================= FUNCTIONS =================

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


def ai_score_resume(resume_text, jd_text):
    prompt = f"""
    Evaluate how well this resume matches the job description.

    Resume:
    {resume_text[:2000]}

    Job Description:
    {jd_text[:1000]}

    Give a match score from 0 to 100.
    Only return the number.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return float(response.choices[0].message.content.strip())
    except:
        return 50


def generate_ai_summary(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a recruitment assistant."},
                {"role": "user", "content": f"Summarize this resume:\n{text[:2000]}"}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return "Summary not available"

# ================= HEADER =================
st.markdown("""
<h1 style='text-align: center; color: white;'>
🧠 AI Recruitment ATS
</h1>
<p style='text-align: center; color: #cbd5f5; font-size:18px;'>
Smart Resume Screening & Candidate Intelligence Platform
</p>
""", unsafe_allow_html=True)
# ================= SIDEBAR =================

st.sidebar.markdown("""
<h2 style='color:white;'>🧠 ATS Panel</h2>
""", unsafe_allow_html=True)

# Navigation
st.sidebar.markdown("### 🧭 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📥 Screening", "📊 Dashboard", "📂 Pipeline"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] {
    background: #020617;
}
</style>
""", unsafe_allow_html=True)

# Filters
st.sidebar.markdown("### ⚙️ Filters")

min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
min_exp = st.sidebar.slider("Minimum Experience", 0, 10, 0)

st.sidebar.markdown("---")

# Instructions
st.sidebar.markdown("### 📌 Instructions")

st.sidebar.info("""
1. Upload resumes (PDF/DOCX)
2. Paste job description
3. Click Analyze
4. Review candidates
""")

st.sidebar.markdown("---")

# System Info
st.sidebar.markdown("### 📊 System Status")
st.sidebar.success("✅ AI Engine Active")
st.sidebar.success("✅ ATS Ready")
# ================= TABS =================
tab1, tab2, tab3 = st.tabs([
    "📥 Resume Screening",
    "📊 Dashboard",
    "📂 Candidate Pipeline"
])

# ================= TAB 1 =================
with tab1:

    uploaded_files = st.file_uploader(
        "Upload Resumes",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )

    jd_text = st.text_area("Paste Job Description")

    analyze = st.button("🚀 Analyze Candidates")

    if analyze:

        if not uploaded_files or not jd_text:
            st.warning("Please upload resumes and enter job description")

        else:
            results = []

            for file in uploaded_files:
                text = extract_text(file)

                score = ai_score_resume(text, jd_text)
                exp = extract_experience(text)

                results.append({
                    "Candidate": file.name,
                    "Score": score,
                    "Experience": exp,
                    "Summary": generate_ai_summary(text)
                })

            df = pd.DataFrame(results)

            # Filters
            df = df[(df["Score"] >= min_score) & (df["Experience"] >= min_exp)]
            df = df.sort_values(by="Score", ascending=False)

            # Status
            df["Status"] = df["Score"].apply(
                lambda x: "Shortlisted" if x >= 70 else
                          "Review" if x >= 40 else
                          "Rejected"
            )

            # KPIs
            st.markdown('<div class="glass">', unsafe_allow_html=True)

            st.subheader("📊 Overview")

            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Avg Score", round(df["Score"].mean(), 2))
            col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

            st.markdown('</div>', unsafe_allow_html=True)
            
            # TOP CANDIDATES WITH BUTTONS
            st.subheader("🏆 Top Candidates")

            top_df = df.head(5)

            for i, row in top_df.iterrows():

                candidate = row["Candidate"]

                st.markdown(f"""
                <div class="glass">
                <h3>👤 {candidate}</h3>
                <p>Score: {row['Score']}% | Experience: {row['Experience']} yrs</p>
                <p>Status: {row['Status']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)

                if col1.button("✅ Shortlist", key=f"short_{i}"):
                    st.session_state["decisions"][candidate] = "Shortlisted"

                if col2.button("❌ Reject", key=f"reject_{i}"):
                    st.session_state["decisions"][candidate] = "Rejected"

                note = col3.text_input("📝 Notes", key=f"note_{i}")

                if note:
                    st.session_state["decisions"][candidate + "_note"] = note

                decision = st.session_state["decisions"].get(candidate)
                if decision:
                    st.success(f"Decision: {decision}")

                note_val = st.session_state["decisions"].get(candidate + "_note")
                if note_val:
                    st.info(f"Note: {note_val}")

                st.progress(int(row["Score"]))
                st.markdown("---")

            # TABLE
            st.subheader("📋 All Candidates")
            st.dataframe(df, use_container_width=True)

# ================= TAB 2 =================
with tab2:

    st.subheader("📊 Hiring Dashboard")

    if 'df' in locals() and not df.empty:

        col1, col2, col3 = st.columns(3)

        col1.metric("Total", len(df))
        col2.metric("Avg Score", round(df["Score"].mean(), 2))
        col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

        st.bar_chart(df.set_index("Candidate")["Score"])

    else:
        st.info("Run screening first")

# ================= TAB 3 =================
with tab3:

    st.subheader("📂 Candidate Pipeline")

    if 'df' in locals() and not df.empty:

        df["Stage"] = df["Score"].apply(
            lambda x: "Interview" if x >= 80 else
                      "Review" if x >= 60 else
                      "Rejected"
        )

        if "decisions" in st.session_state:
            decisions = st.session_state["decisions"]
            df["Recruiter Decision"] = df["Candidate"].map(decisions).fillna("Pending")
        else:
            df["Recruiter Decision"] = "Pending"

        st.dataframe(df, use_container_width=True)

        st.bar_chart(df["Stage"].value_counts())

    else:
        st.info("No candidates yet")
