from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from dotenv import load_dotenv
import base64
import os
import io
from PIL import Image
import fitz
import google.generativeai as genai
import json
from typing import Dict, Union
import re

app = FastAPI()

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Set your custom API key for verification
API_KEY = os.getenv("API_KEY")

# API Key Verification
def verify_api_key(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Input File Setup
def input_file_setup(uploaded_file: UploadFile, file_type: str):
    try:
        file_content = []
        if file_type == 'pdf':
            pdf_document = fitz.open(stream=uploaded_file.file.read(), filetype="pdf")
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap()
                img_byte_arr = io.BytesIO(pix.tobytes("jpeg"))
                img_byte_arr = img_byte_arr.getvalue()
                file_content.append({
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(img_byte_arr).decode()
                })
        elif file_type in ['jpg', 'jpeg', 'png']:
            image = Image.open(uploaded_file.file)
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            file_content.append({
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            })
        return file_content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {e}")

# GST Calculation
def calculate_gst(data):
    for product in data.get("finalValues", []):
        gst_percentage = 18
        if "CGST%" in product and product["CGST%"] is not None:
            gst_percentage = 2 * product["CGST%"]
        elif "SGST%" in product and product["SGST%"] is not None:
            gst_percentage = 2 * product["SGST%"]
        elif "IGST%" in product and product["IGST%"] is not None:
            gst_percentage = product["IGST%"]
        
        # Calculate GST values
        if(product["totalAmountWithGST"] is not None):
            total_price = round(product["totalAmountWithGST"] / (1 + gst_percentage / 100), 2)
        total_price = product["totalAmountWithoutGST"] 
        product["gst"] = round(total_price * gst_percentage / 100, 2)
    
    return data

# Generate Response Using Gemini
def get_gemini_response(file_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([page for page in file_content] + [prompt])

    # Remove leading "json" line (if present)
    cleaned_response = response.text
    # Remove unwanted prefix using regular expressions
    cleaned_response = re.sub(r"^[\s\S]*?({)", r"\1", cleaned_response)  # Match any characters followed by "{"
    cleaned_response = cleaned_response[:-3]

    if not cleaned_response:
        raise HTTPException(status_code=500, detail="Empty response from Gemini")
    
    try:
        response_json = json.loads(cleaned_response)
        return calculate_gst(response_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from Gemini")

# API Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Parsing System!"}

@app.post("/parse-invoice/")
async def parse_invoice(api_key: str = Depends(verify_api_key), file: UploadFile = File(...)):
    file_type = file.filename.split('.')[-1].lower()
    file_content = input_file_setup(file, file_type)

    prompt = """
    You are an expert in reading and extracting important details from invoices. Please extract the following details from the uploaded invoice and return them in the given format. 
    {
        "id": "32784d8c-22f7-4e78-a6a8-fb693f47258c",
        "totalAmount": 2100,
        "refNo": "111",
        "vendor": {
            "id": "198ab4b9-7be0-4426-828a-5bf4b1e8b57b",
            "companyName": "DELL INTERNATIONAL SERVICES INDIA PRIVATE LIMITED",
            "email": "vendor@dell.com",
            "mobile": "9876543211",
            "address": "Crystal Downs, Survey No. 7/1, 7/2, 7/3, Embassy Golf Links Business Park, Off-Intermediate Ring Road, Domlur, Challaghatta Village, Varthur Hobli, Bengaluru, Bengaluru Urban, Karnataka, 560071",
            "customerState": "AS",
            "customerCity": "Barpeta",
            "country": "India",
            "zip": "560071",
            "gstin": "29AAACH1925Q1Z6",
            "pan": "AAACH1925Q"
        },
        "products": [
            {
                "id": "dee77aa6-a999-40e1-89a4-2d105437bf41",
                "rfpProductId": "c5b48f40-26a5-42d1-a7ce-cd38d87499ae",
                "name": "Coffee Maker",
                "modelNo": "CM454",
                "quantity": 1,
                "price": 1000,
                "description": "Caffiene Master",
                "gst": 5,
                "type": "product"
            },
            {
                "name": "Other Charges (if any)",
                "price": 1000,
                "gst": 5,
                "type": "otherCharge"
            },
        ],
        "finalValues" :[ 
            {
                "CGST%" : 8
                "SGST%" : 8
                "IGST%" : 10
                "totalAmountWithoutGST": 2000,
                "totalAmountWithGST": 3000,
            }
        ],

        "supportingDocuments": [
            {
                "documentName": "2024-10-15-Tsts.pdf",
                "location": "https://utfs.io/f/MwCVYPRyYlZWZi1cQAmbV4BdKtq6Nc5zOfvSaD1iRC3yGJmk"
            }
        ]
    }
    Make sure the it is well-formed and each key value in new line. Do not use any extra commentaries or words. 
    """

    response = get_gemini_response(file_content, prompt)
    return response  # Directly return the response JSON object

@app.get("/health/")
def health_check():
    return {"status": "API is up and running"}

# Run Application
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
