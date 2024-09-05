from dotenv import load_dotenv

load_dotenv()
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(input, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input, pdf_content[0], prompt])
    return response.text

def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        ## Convert the PDF to image
        images = pdf2image.convert_from_bytes(uploaded_file.read())
        first_page = images[0]

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()  # encode to base64
            }
        ]
        return pdf_parts
    else:
        raise FileNotFoundError("No file uploaded")

## Streamlit App

st.set_page_config(page_title="ATS Resume Expert")
st.header("ATS Tracking System")

input_text = st.text_area("Job Description: ", key="input")
uploaded_file = st.file_uploader("Upload your resume(PDF)...", type=["pdf"])

if uploaded_file is not None:
    st.write("PDF Uploaded Successfully")

submit1 = st.button("Resume Evaluation")  # More descriptive button text
submit2 = st.button("Skill Improvement Suggestions")
submit3 = st.button("Percentage Match & Missing Keywords")

input_prompt1 = """
You are an experienced Technical Human Resource Manager, tasked with reviewing the provided resume against the job description.
Please share your professional evaluation on whether the candidate's profile aligns with the role.
Highlight the candidate's strengths and areas for improvement based on the job requirements.
"""

input_prompt2 = """
You are a skilled career advisor with deep knowledge of in-demand skills. Based on the provided job description
and the candidate's resume, identify areas where the candidate can improve their skills to become a more
competitive applicant. Offer specific suggestions for skill development.
"""

input_prompt3 = """
You are an expert ATS (Applicant Tracking System) scanner with a sophisticated understanding of data science and ATS functionality.
Your task is to evaluate the resume against the provided job description.
- Provide a percentage match between the resume and job description.
- Identify any keywords that are missing from the resume but are present in the job description.
- Offer final thoughts on the resume's suitability for the job.
"""

if submit1:
    if uploaded_file is not None:
        pdf_content = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt1, pdf_content, input_text)
        st.subheader("Resume Evaluation")
        st.write(response)
    else:
        st.write("Please upload the resume")

elif submit2:
    if uploaded_file is not None:
        pdf_content = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt2, pdf_content, input_text)
        st.subheader("Skill Improvement Suggestions")
        st.write(response)
    else:
        st.write("Please upload the resume")

elif submit3:
    if uploaded_file is not None:
        pdf_content = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_prompt3, pdf_content, input_text)
        st.subheader("Percentage Match & Missing Keywords")
        st.write(response)
    else:
        st.write("Please upload the resume")