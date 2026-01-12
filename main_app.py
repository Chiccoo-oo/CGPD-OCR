import gradio as gr
import pandas as pd
import ollama
import pdfplumber
import easyocr
import cv2
import numpy as np
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

# --- INITIALIZATION ---
# Initialize the Standalone OCR Engine (Hindi and English)
# This stays 100% offline after the first run
reader = easyocr.Reader(['hi', 'en'])

# --- CORE FUNCTIONS ---

def improve_and_ocr(image_path):
    """Pre-processes images for better OCR and extracts structured data using Llama 3.2"""
    if image_path is None: return "No image uploaded.", "No image uploaded."
    
    # 1. Image Enhancement for low-quality FIRs
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0) # Increase contrast
    
    # 2. Local OCR Extraction
    results = reader.readtext(gray, detail=0)
    full_text = "\n".join(results)
    
    # 3. AI Categorization for FIR Details
    prompt = f"""
    Analyze this messy FIR text and extract information into these EXACT categories in Hindi:
    1. अपराध विवरण (FIR No, Section, Date)
    2. पक्षकारों का विवरण (Complainant Name, Accused/Suspect Description)
    3. घटना का सारांश (Items stolen, Mode of crime)

    TEXT: {full_text}
    """
    try:
        # Forces CPU usage to avoid cudaMalloc errors
        response = ollama.generate(model='llama3.2', prompt=prompt)
        return full_text, response['response']
    except Exception as e:
        return full_text, f"Ollama Error: {str(e)}"

def generate_official_reply(excel_file, pdf_file):
    """Generates official Vidhan Sabha drafts by combining PDF questions and Excel stats"""
    os.makedirs("data/outputs", exist_ok=True)
    
    # 1. Load Data
    try:
        df = pd.read_excel(excel_file.name)
        df = df.fillna("-")
    except Exception as e:
        return f"Excel Error: {e}", None

    # 2. Extract Question Context from PDF
    q_text = ""
    try:
        with pdfplumber.open(pdf_file.name) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text: q_text += text
    except Exception as e:
        return f"PDF Error: {e}", None

    # 3. Create Formal Word Document
    doc = Document()
    
    # Center-Aligned Header
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("छत्तीसगढ़ विधान सभा सचिवालय\n")
    run.bold = True
    run.font.size = Pt(16)
    
    doc.add_heading('प्रारुप उत्तर (Draft Answer)', level=1)
    doc.add_paragraph("विभाग का नाम: गृह विभाग")
    
    # AI Summary for the Cover Page
    prompt = f"Write a 4-line formal Hindi summary for Vidhan Sabha. Context: {q_text[:500]}. Data: {df.head().to_string()}."
    response = ollama.generate(model='llama3.2', prompt=prompt)
    doc.add_paragraph(response['response'])

    # 4. Appendix Table (The Table Grid)
    doc.add_page_break()
    doc.add_heading('परिशिष्ट "अ"', level=2)
    
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = 'Table Grid'
    
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr_cells[i].text = str(col)
        hdr_cells[i].paragraphs[0].runs[0].bold = True
    
    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)

    out_path = "data/outputs/Official_Vidhan_Sabha_Draft.docx"
    doc.save(out_path)
    return response['response'], out_path

# --- GRADIO UI LAYOUT ---

with gr.Blocks(theme=gr.themes.Soft(), title="Police Standalone AI") as demo:
    gr.Markdown("# 👮 Chhattisgarh Police Integrated AI Desk")
    gr.Markdown("Fully Offline System for Data Analytics, Policy, and FIR Extraction")
    
    with gr.Tabs():
        # TAB 1: Vidhan Sabha & Data Analytics
        with gr.TabItem("Vidhan Sabha Dashboard"):
            gr.Markdown("### Upload Excel Stats and Question PDF for Official Draft")
            with gr.Row():
                ex_in = gr.File(label="1. Upload Crime Excel")
                pdf_in = gr.File(label="2. Upload Question PDF")
            btn_v = gr.Button("Generate Professional Draft", variant="primary")
            with gr.Row():
                v_out_txt = gr.TextArea(label="AI Formal Intro (Hindi)")
                v_out_file = gr.File(label="Download Word Report")
            btn_v.click(generate_official_reply, [ex_in, pdf_in], [v_out_txt, v_out_file])

        # TAB 2: Advanced OCR & FIR Summarizer
        with gr.TabItem("FIR OCR & Extraction"):
            gr.Markdown("### Upload Image of FIR/Document for Data Extraction")
            with gr.Row():
                img_in = gr.Image(type="filepath", label="Upload Photo")
                with gr.Column():
                    raw_ocr = gr.TextArea(label="Raw Extracted Text")
                    smart_summary = gr.TextArea(label="Categorized Details (AI)")
            btn_o = gr.Button("Process Document", variant="secondary")
            btn_o.click(improve_and_ocr, inputs=img_in, outputs=[raw_ocr, smart_summary])

# --- LAUNCH ---
if __name__ == "__main__":
    # Ensure Ollama is running on CPU to avoid memory crashes
    os.environ["OLLAMA_MAX_VRAM"] = "0"
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    
    demo.launch()