from dotenv import load_dotenv
import base64
import streamlit as st  
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
import json



load_dotenv()


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_gemini_response(file_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([file_content[0], prompt])
    
    
    try:
        response_json = json.loads(response.text)  
        return response_json
    except json.JSONDecodeError:
        
        # st.error("Failed to parse the response as JSON. Displaying raw output.")
        return response.text


def input_file_setup(uploaded_file, file_type):
    if uploaded_file is not None:
        if file_type == 'pdf':
            
            images = pdf2image.convert_from_bytes(uploaded_file.read())
            first_page = images[0]

            
            img_byte_arr = io.BytesIO()
            first_page.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()

        elif file_type in ['jpg', 'jpeg', 'png']:
            
            image = Image.open(uploaded_file)

          
            if image.mode == 'RGBA':
                image = image.convert('RGB')

            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')  
            img_byte_arr = img_byte_arr.getvalue()

        
        file_content = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()  
            }
        ]
        return file_content
    else:
        raise FileNotFoundError("No file uploaded")


st.set_page_config(page_title="Invoice Parsing System")
st.header("Invoice Parsing System")


uploaded_file = st.file_uploader("Upload your Invoice (PDF, JPG, JPEG, PNG)...", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.write("File Uploaded Successfully")


submit1 = st.button("Extract Invoice Details")


input_prompt = """
You are an expert in reading and extracting important details from invoices. Please extract the following details from the uploaded invoice and return them in a valid JSON format:
- Order No.
- Ref
- Sanskrit Id
- Date
- GSTIN
- Credits Required
- Handling Cost
- Total Cost
- Unit Price, Quantity, Total Price, IGST, and Total Price inclusive of all taxes
- Invoice To and Ship To addresses

Make sure the JSON is well-formed and includes no extra commentary or text.
Make json response as an object named Product . Give output in multiple lines.
"""


if submit1:
    if uploaded_file is not None:
        
        file_type = uploaded_file.name.split('.')[-1].lower()

        
        file_content = input_file_setup(uploaded_file, file_type)

        
        response = get_gemini_response(file_content, input_prompt)

        
        if isinstance(response, dict):  
            st.subheader("Extracted Invoice Details (JSON):")
            st.json(response)
        else:
            st.subheader("Extracted Invoice Details (JSON):")
            st.write(response)  
    else:
        st.write("Please upload the invoice")
