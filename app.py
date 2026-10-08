import json
import os
import re
import streamlit as st
from dotenv import load_dotenv
from docx import Document
from pypdf import PdfReader
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY","GEMINI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL","GEMINI_MODEL")

REPORT_SECTIONS = [
    ("strengths", "Strengths"),
    ("gaps", "Gaps"),
    ("missing_skills", "Missing Skills"),
    ("improvements", "Improvements"),
    ("overall_summary", "Overall Summary")
]



def extract_resume_text(uploaded_file):
    """Return the plain text content of the uploaded resume file."""
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = []

        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()
    
    if file_name.endswith(".docx"):
        document = Document(uploaded_file)
        paragraphs = []

        for paragraph in document.paragraphs:
            paragraphs.append(paragraph.text)
        return "\n".join(paragraphs).strip()
    
    return "NO INPUT WAS GIVEN AS CV , ASK THE USER TO UPLOAD A CV"



def analyze_resume(resume_text, job_description):
    """LLM call #1: Turn the resume and job description into a structured JSON report."""
    client = OpenAI(api_key=API_KEY)
    instructions = """You compare resumes against job descriptions and
      return a structured JSON report with the following sections: strengths, gaps, missing_skills, improvements, overall_summary. Each section should contain a list of bullet points.
        The output must be valid JSON.
        {
        "candidate_skills":[],
        "Candidate_experience":[],
        "candidate_qualification":[],
        "required_skills":[],
        "strengths":[],
        "gaps":[],
        "missing_skills":[],
        "improvements":[],
        "overall_summary":[]
        }

        Rules: 
        - Use only the information provided in the resume and job description to fill out the report.
        - Never invent skills, employers, job titles, dates etc
        - "missing_skills" should only include skills that are explicitly mentioned in the job description but not present in the resume.
        - Leave a list empty if there are no items to report in a section.
        """
    user_message = f"""
                    Compare this resume against this job description and return a structured JSON report as per the instructions above.
                    
                    Resume:
                    {resume_text}

                    Job Description:
                    {job_description}            
        """

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=user_message,
        text={"format":{"type":"json"}}
    )
    return json.loads(response.output_text)








def generate_final_report(structured_analysis):
    """LLM call #2: Turn the structured JSON report into a human-readable final report."""
    client = OpenAI(api_key=API_KEY)
    instructions = """
Analyze the provided resume and generate a professional **Final Resume Evaluation Report**.

Evaluate the candidates profile, education, skills, projects, experience, certifications, ATS compatibility, strengths, weaknesses, missing information, and job readiness. Give an **overall score out of 100**, explain the score, identify the most important improvements, and provide a short actionable improvement plan. Tailor the analysis to the target job role if provided.

**Rules:**

* Use only information available in the resume.
* Do not invent or assume facts.
* Be honest, objective, and recruiter-focused.
* Keep the report clear, concise, and actionable.
* Highlight both strengths and weaknesses.
* Separate existing skills from recommended skills.
* Prioritize the most important improvements.
* Evaluate ATS readability, keywords, formatting, and role relevance.
* Mention missing information that could strengthen the resume.
* If a target role is provided, tailor the evaluation specifically to that role.
* End with a concise final verdict and scorecard.
"""

    user_message = f"""
    Turn this structed JSON report into a professional, human-readable **Final Resume Evaluation Report**.
    {json.dumps(structured_analysis, indent=2)}
    """

    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=user_message,
        text={"format":{"type":"text"}}
    )
    report = json.loads(response.output_text)


    for key, _ in REPORT_SECTIONS:
        value = report.get(key)
        if isinstance(value, list):
              value = "\n".join("- "+str(point) for point in value)
        report[key] = value or "Nothing was reported for this session"

    return report  





def create_downloadble_report(final_report):
    """Build the markdown text for the resume_analysis.md download"""
    lines = ["# Resume Analysis"]
    for key, heading in REPORT_SECTIONS:
        lines.append(f"##{heading}")
        lines.append(final_report[key])
    return "\n\n".join(lines)


def main():
    st.set_page_config(page_title="AI Resume Analyzer")
    st.title("AI Resume Analyzer")
    st.write(
        "Upload your resume and paste a JOB Description to identify strengths," \
        "gaps and improvement opportunities"
    )
    uploaded_file=st.file_uploader("Upload your resume", type={"pdf","docx"})
    job_description = st.text_area("Paste the Job Description", height=250)

    if st.button("Analyze Resume"):
        if uploaded_file is None:
            st.warning("Please upload resume")
            st.stop()

        if not job_description.strip():
            st.warning("Please paste the JD")
            st.stop()

        resume_text = extract_resume_text(uploaded_file)

        if not resume_text:
            st.warning("No text could be read from your resume file, try different format")

        if not API_KEY:
            st.error("NO API KEY was found in .env file")

        with st.spinner("Analyze your resume ...."):
            try:
                structured_analysis = analyze_resume(resume_text, job_description)
                final_report = generate_final_report(structured_analysis)
            except Exception as error:
                st.error(f"The analysis failed:{ error}")
                st.stop()

        st.session_state["final_report"] = final_report

        if "final_report" in st.session_state:
            final_report = st.session_state["final_report"]

            st.divider()
            st.subheader("Analysis Results")

            for key,heading in REPORT_SECTIONS:
                st.markdown(f"###", {heading})
                st.markdown(final_report[key])

                st.download_button(
                    "Download report",
                    data= create_downloadble_report(final_report),
                    file_name = "resume_analysis.md",
                )

if __name__=="__main__":
    main()



https://github.com/Jayant-90/Gen_AI.git