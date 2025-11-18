# core/extract_AI.py
import io
from docx import Document
from google import generativeai as genai
from utils_pro import extract_text_from_docx  

genai.configure(api_key="YOUR_GEMINI_API_KEY")

def extract_with_ai(docx_file):
    # Extract raw paragraphs from DOCX
    text = extract_text_from_docx(docx_file)

    # Send to Gemini for classification
    prompt = f"""
You are an AI trained to extract structured assessment questions from exam papers.

Classify each block into:
- parent_question
- sub_question
- case_study
- table
- figure
Return a list of dictionaries with:
- number (e.g. "1.1.1")
- text
- type (e.g. parent_question or sub_question)
- marks (if visible)
- parent_number (optional, if sub_question)

Here is the input content:
{text}
"""

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text
