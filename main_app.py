import gradio as gr
import pandas as pd
import ollama
import pdfplumber
from docx import Document
import os

def generate_official_reply(excel_file, pdf_file):
    os.makedirs("data/outputs", exist_ok=True)
    # 1. Read Excel Stats
    try:
        df = pd.read_excel(excel_file.name)
        excel_context = df.to_string() # Convert table to readable text
    except Exception as e:
        return f"Excel Error: {e}", None

    # 2. Read PDF Questions
    questions_text = ""
    try:
        with pdfplumber.open(pdf_file.name) as pdf:
            for page in pdf.pages:
                questions_text += page.extract_text()
    except Exception as e:
        return f"PDF Error: {e}", None

    # 3. Load Local Policies
    with open("data/policies/rules.txt", "r", encoding="utf-8") as f:
        policies = f.read()

    # 4. Prompt the Local LLM (Llama 3.2)
    prompt = f"""
    ROLE: Chhattisgarh Police Assistant
    DATA: {excel_context}
    POLICIES: {policies}
    QUESTIONS: {questions_text}

    TASK: Answer the questions based ONLY on the data and policies provided. 
    Format as an official 'प्रारुप उत्तर' in Hindi.
    """

    response = ollama.generate(model='llama3.2', prompt=prompt)
    hindi_ans = response['response']

    # 5. Export to Word
    doc = Document()
    doc.add_heading('छत्तीसगढ़ विधान सभा - उत्तर प्रारूप', 0)
    doc.add_paragraph(hindi_ans)
    out_path = "data/outputs/Official_Draft.docx"
    doc.save(out_path)
    
    return hindi_ans, out_path

# --- UI Setup ---
with gr.Blocks() as demo:
    gr.Markdown("# 👮 Police AI: Vidhan Sabha Automated Desk")
    with gr.Row():
        ex_in = gr.File(label="Upload Crime Excel")
        pdf_in = gr.File(label="Upload Question PDF")
    btn = gr.Button("Generate Draft Answer", variant="primary")
    out_txt = gr.TextArea(label="AI Draft (Hindi)")
    out_file = gr.File(label="Download Report")

    btn.click(generate_official_reply, [ex_in, pdf_in], [out_txt, out_file])

demo.launch()