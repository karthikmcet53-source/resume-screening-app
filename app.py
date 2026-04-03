import streamlit as st
import docx
import PyPDF2
import pandas as pd
import re
from openai import OpenAI
import os
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
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


def score_resume(resume_text, jd_text):
    resume_words = set(resume_text.lower().split())
    jd_words = set(jd_text.lower().split())
    score = len(resume_words & jd_words) / len(jd_words) if jd_words else 0
    return round(score * 100, 2)
def generate_ai_summary(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a recruitment assistant."},
                {"role": "user", "content": f"Summarize this resume in 2 lines highlighting experience, skills and role:\n{text[:2000]}"}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return "Summary not available"

# Page config
st.set_page_config(page_title="AI Recruitment ATS",layout="wide")

# ================= HEADER =================
st.markdown("""
# 🧠 AI Recruitment Dashboard
### Intelligent Candidate Screening System
""")

# ================= SIDEBAR =================
st.sidebar.markdown("## 🧭 Navigation")
page = st.sidebar.radio("Go to", ["Screening Dashboard"])

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Filters")

min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
min_exp = st.sidebar.slider("Minimum Experience", 0, 10, 0)

st.sidebar.markdown("---")
st.sidebar.markdown("## 📌 Instructions")
st.sidebar.info("""
Upload resumes → Enter JD → Analyze → Filter candidates
""")
# ================= TABS =================
tab1, tab2, tab3 = st.tabs([
    "📥 Resume Screening",
    "📊 Dashboard",
    "📂 Candidate Pipeline"
])
with tab1:
    st.markdown("### 📂 Upload Candidate Resumes")
    uploaded_files = st.file_uploader(
    "Upload Files",
    type=["pdf", "docx"],
    accept_multiple_files=True
    )

    st.markdown("### 📝 Job Description")
    jd_text = st.text_area("Enter job description", height=120)

    st.markdown("---")

    col1, col2, col3 = st.columns([1,2,1])
    analyze = col2.button("🚀 Run Screening")

    # ================= RESULTS =================
    # ================= RESULTS =================
if analyze:

    if not uploaded_files or not jd_text:
        st.warning("Please upload resumes and enter job description")

    else:
        results = []

        for file in uploaded_files:
            text = extract_text(file)

            score = score_resume(text, jd_text)
            exp = extract_experience(text)

            results.append({
                "Candidate": file.name,
                "Score": score,
                "Experience": exp,
                "Summary": generate_ai_summary(text)
            })
        df = pd.DataFrame(results)

        # Apply filters
        df = df[(df["Score"] >= min_score) & (df["Experience"] >= min_exp)]

        df = df.sort_values(by="Score", ascending=False)

        # Status column
        df["Status"] = df["Score"].apply(
            lambda x: "🟢 Shortlisted" if x >= 70 else "🔴 Rejected"
        )

        # ================= KPI =================
        st.markdown("## 📊 Overview")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Candidates", len(df))
        col2.metric("Avg Score", round(df["Score"].mean(), 2))
        col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

        st.markdown("---")

        # ================= TOP =================
        st.markdown("## 🏆 Top Candidates")

        top_df = df.head(5)

        for _, row in top_df.iterrows():
            st.markdown(f"""
            **{row['Candidate']}**  
            Score: {row['Score']}% | Experience: {row['Experience']} yrs  
            Status: {row['Status']}
            """)
            st.progress(int(row["Score"]))

        st.markdown("---")

        # ================= TABLE =================
        st.markdown("## 📋 Candidate Pipeline")

        def color_score(val):
            if val >= 75:
                return "background-color: #D4EDDA"
            elif val >= 50:
                return "background-color: #FFF3CD"
            else:
                return "background-color: #F8D7DA"

        styled_df = df.style.map(color_score, subset=["Score"])

        st.dataframe(styled_df, use_container_width=True)

        # ================= DOWNLOAD =================
        st.markdown("### 📥 Export Data")

        csv = df.to_csv(index=False).encode('utf-8')

        st.download_button(
            "Download Candidate List",
            csv,
            "candidates.csv",
            "text/csv"
        )
with tab2:
    st.subheader("📊 Hiring Dashboard")

    try:
        if 'df' in locals() and not df.empty:

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Candidates", len(df))
            col2.metric("Avg Score", round(df["Score"].mean(), 2))
            col3.metric("Shortlisted", len(df[df["Score"] >= 70]))

            st.markdown("### Score Distribution")
            st.bar_chart(df.set_index("Candidate")["Score"])

        else:
            st.info("Run screening to see dashboard")

    except:
        st.info("No data available yet")
with tab3:
    st.subheader("📂 Candidate Pipeline")

    try:
        if 'df' in locals() and not df.empty:

            df["Stage"] = df["Score"].apply(
                lambda x: "Interview" if x >= 80 else
                          "Review" if x >= 60 else
                          "Rejected"
            )

            st.dataframe(df, use_container_width=True)

            st.markdown("### Pipeline Distribution")
            st.bar_chart(df["Stage"].value_counts())

        else:
            st.info("No candidates available")

    except:
        st.info("Run screening first")
