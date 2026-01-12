import gradio as gr
import pandas as pd
import ollama
import pdfplumber
import easyocr
import cv2
import numpy as np
from docx import Document
import os

# Initialize OCR
reader = easyocr.Reader(['hi', 'en'])

def improve_and_ocr(image_path):
    """Cleans image and extracts text"""
    if image_path is None: return "No image uploaded."
    
    # 1. Image Pre-processing (Gray scale & Contrast)
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # 2. Extract Text
    results = reader.readtext(gray, detail=0)
    full_text = "\n".join(results)
    
    # 3. AI Smart Extraction
    # Using Llama 3.2 to find specific FIR details from the messy OCR text
    prompt = f"""
    Below is text from a police FIR image. Extract only these details in Hindi:
    - FIR Number (अपराध क्रमांक)
    - Section (धारा)
    - Date (दिनांक)
    - Accused Name (आरोपी का नाम)
    - Brief Summary (संक्षिप्त विवरण)
    
    TEXT: {full_text}
    """
    response = ollama.generate(model='llama3.2', prompt=prompt)
    return full_text, response['response']

def generate_vidhan_sabha(excel_file, pdf_file):
    os.makedirs("data/outputs", exist_ok=True)
    df = pd.read_excel(excel_file.name).fillna("-")
    
    # Extract Q from PDF
    with pdfplumber.open(pdf_file.name) as pdf:
        q_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

    # Create Word Report with Official Table
    doc = Document()
    doc.add_heading('छत्तीसगढ़ विधान सभा - प्रारूप उत्तर', 0)
    
    prompt = f"Write a formal Hindi police report summary for these questions: {q_text[:500]} based on this data: {df.head().to_string()}"
    res = ollama.generate(model='llama3.2', prompt=prompt)
    doc.add_paragraph(res['response'])
    
    # Add Table (Appendix A)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = 'Table Grid'
    for i, col in enumerate(df.columns):
        table.rows[0].cells[i].text = str(col)
    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)

    path = "data/outputs/Vidhan_Sabha_Reply.docx"
    doc.save(path)
    return res['response'], path

# --- Improvised UI ---
with gr.Blocks(theme=gr.themes.Default()) as demo:
    gr.Markdown("# 👮 Advanced Police AI Desk (Standalone)")
    
    with gr.Tabs():
        # TAB 1: Vidhan Sabha & Data
        with gr.TabItem("Vidhan Sabha & Stats"):
            with gr.Row():
                ex_in = gr.File(label="Upload Crime Excel")
                pdf_in = gr.File(label="Upload Question PDF")
            btn_v = gr.Button("Generate Official Document", variant="primary")
            v_out_txt = gr.TextArea(label="Draft Summary (Hindi)")
            v_out_file = gr.File(label="Download Report")
            btn_v.click(generate_vidhan_sabha, [ex_in, pdf_in], [v_out_txt, v_out_file])

        # TAB 2: Advanced FIR OCR & Summarizer
        with gr.TabItem("FIR OCR & Extraction"):
            gr.Markdown("### Upload FIR Image to extract key details automatically")
            with gr.Row():
                img_in = gr.Image(type="filepath", label="Upload FIR Photo")
                with gr.Column():
                    raw_ocr = gr.TextArea(label="Raw Extracted Text")
                    smart_summary = gr.TextArea(label="Smart FIR Details (AI)")
            btn_o = gr.Button("Process FIR Image", variant="secondary")
            btn_o.click(improve_and_ocr, inputs=img_in, outputs=[raw_ocr, smart_summary])

demo.launch()