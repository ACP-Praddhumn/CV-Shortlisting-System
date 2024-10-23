from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from dotenv import load_dotenv
import base64
import os
import io
from PIL import Image
import fitz  
import google.generativeai as genai
import json
import uvicorn

app = FastAPI()

# Load environment variables from .env file
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# API Key for authentication
API_KEY = os.getenv("API_KEY")

# Function to verify the API key
def verify_api_key(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Function to handle file processing (PDFs or images)
def input_file_setup(uploaded_file: UploadFile, file_type: str):
    try:
        file_content = []  # To store content for each page/image
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

# Function to get response from Google Generative AI
def get_gemini_response(file_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([page for page in file_content] + [prompt])
    try:
        response_json = json.loads(response.text)
        return response_json
    except json.JSONDecodeError:
        return response.text

# FastAPI route for parsing invoices
@app.post("/parse-invoice/")
async def parse_invoice(api_key: str = Depends(verify_api_key), file: UploadFile = File(...)):
    file_type = file.filename.split('.')[-1].lower()
    file_content = input_file_setup(file, file_type)

    prompt = """
    You are an expert in reading and extracting important details from invoices. Please extract the following details from the uploaded invoice and return them in a valid JSON format:
    {
      "id": "32784d8c-22f7-4e78-a6a8-fb693f47258c",
      "totalAmount": 2100,
      "refNo": "111",
      "totalAmountWithoutGST": 2000,
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
        }
      ],
      "supportingDocuments": [
        {
          "documentName": "2024-10-15-Tsts.pdf",
          "location": "https://utfs.io/f/MwCVYPRyYlZWZi1cQAmbV4BdKtq6Nc5zOfvSaD1iRC3yGJmk"
        }
      ]
    }
    Make sure the JSON is well-formed and includes no extra commentary or text.
    Make JSON response as an object. Give output in multiple lines. The given format is just an example.
    """
    response = get_gemini_response(file_content, prompt)
    return {"data": response}

# Health check route
@app.get("/health/")
def health_check():
    return {"status": "API is up and running"}

# Uvicorn server setup for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Get the port from the environment variable or default to 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port)
