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

        score = response.choices[0].message.content.strip()
        return float(score)

    except:
        return 50  # fallback
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
            lambda x: "🟢 Shortlisted" if x >= 70 else 
                      "🎈Review" if x >= 40 else 
                      "🔴 Rejected" 
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

        for i, row in top_df.iterrows():

    candidate = row["Candidate"]

    st.markdown(f"""
    ### 👤 {candidate}
    Score: {row['Score']}% | Experience: {row['Experience']} yrs  
    Status: {row['Status']}
    """)

    col1, col2, col3 = st.columns(3)

    # Shortlist button
    if col1.button("✅ Shortlist", key=f"short_{i}"):
        st.session_state["decisions"][candidate] = "Shortlisted"

    # Reject button
    if col2.button("❌ Reject", key=f"reject_{i}"):
        st.session_state["decisions"][candidate] = "Rejected"

    # Notes input
    note = col3.text_input("📝 Notes", key=f"note_{i}")

    # Save note
    if note:
        st.session_state["decisions"][candidate + "_note"] = note

    # Show decision
    if candidate in st.session_state["decisions"]:
        decision = st.session_state["decisions"][candidate]
        st.success(f"Decision: {decision}")

    # Show note
    if candidate + "_note" in st.session_state["decisions"]:
        st.info(f"Note: {st.session_state['decisions'][candidate + '_note']}")

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

        if "decisions" in st.session_state:
            decisions = st.session_state["decisions"]
            df["Recruiter Decision"] = df["Candidate"].map(decisions).fillna("Pending")
        else:
            df["Recruiter Decision"] = "Pending"

        st.dataframe(df, use_container_width=True)

            st.markdown("### Pipeline Distribution")
            st.bar_chart(df["Stage"].value_counts())

        else:
            st.info("No candidates available")

    except:
        st.info("Run screening first")
