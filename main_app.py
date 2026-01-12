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

# Initialize OCR
reader = easyocr.Reader(['hi', 'en'], gpu=False)

def advanced_image_preprocessing(image_path):
    """Enhanced image preprocessing for better OCR accuracy"""
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Noise removal
    kernel = np.ones((1, 1), np.uint8)
    gray = cv2.dilate(gray, kernel, iterations=1)
    gray = cv2.erode(gray, kernel, iterations=1)
    
    # Apply Gaussian Blur
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive thresholding
    gray = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 31, 2
    )
    
    # Deskew if needed
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        if abs(angle) > 0.5:
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), 
                                 flags=cv2.INTER_CUBIC, 
                                 borderMode=cv2.BORDER_REPLICATE)
    
    return gray

def extract_text_from_image(image_path):
    """Clean text extraction from any document image"""
    if image_path is None: 
        return "❌ कोई चित्र अपलोड नहीं किया गया।", ""
    
    try:
        # Preprocess image
        processed_img = advanced_image_preprocessing(image_path)
        
        # Extract text
        results = reader.readtext(
            processed_img, 
            detail=0,
            paragraph=True,
            width_ths=0.7,
            height_ths=0.7
        )
        
        # Join text with proper spacing
        extracted_text = "\n".join(results)
        
        if not extracted_text.strip():
            return "❌ चित्र से कोई पाठ नहीं निकाला जा सका। कृपया स्पष्ट चित्र अपलोड करें।", ""
        
        # Use AI to clean and format the text properly
        prompt = f"""निम्नलिखित OCR से निकाला गया पाठ है जो गड़बड़ या टूटा हुआ हो सकता है। कृपया इसे साफ करें और सही क्रम में व्यवस्थित करें।

OCR पाठ:
{extracted_text}

केवल साफ, पढ़ने योग्य पाठ लौटाएं। कोई अतिरिक्त टिप्पणी न जोड़ें। यदि पाठ हिंदी में है तो हिंदी में रखें, अंग्रेजी में है तो अंग्रेजी में रखें।"""
        
        try:
            response = ollama.generate(
                model='llama3.2', 
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                }
            )
            cleaned_text = response['response']
        except Exception as e:
            # If AI fails, return raw extracted text
            cleaned_text = f"[AI सफाई उपलब्ध नहीं है]\n\n{extracted_text}"
        
        return extracted_text, cleaned_text
        
    except Exception as e:
        return f"❌ त्रुटि: {str(e)}", ""

def generate_vidhan_sabha(excel_file, pdf_file):
    """Generate Vidhan Sabha report"""
    if excel_file is None or pdf_file is None:
        return "❌ कृपया Excel और PDF दोनों फ़ाइलें अपलोड करें।", None
    
    try:
        os.makedirs("data/outputs", exist_ok=True)
        df = pd.read_excel(excel_file.name).fillna("-")
        
        # Extract questions from PDF
        with pdfplumber.open(pdf_file.name) as pdf:
            q_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        if not q_text.strip():
            return "❌ PDF से पाठ निकालने में विफल।", None

        # Create Word document
        doc = Document()
        
        # Add header
        header = doc.sections[0].header
        header_para = header.paragraphs[0]
        header_para.text = "छत्तीसगढ़ पुलिस विभाग"
        header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        header_para.runs[0].font.size = Pt(14)
        header_para.runs[0].font.bold = True
        
        # Add title
        title = doc.add_heading('विधान सभा - प्रारूप उत्तर', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Generate summary
        prompt = f"""निम्नलिखित विधान सभा प्रश्नों के लिए एक औपचारिक हिंदी पुलिस रिपोर्ट सारांश लिखें।

प्रश्न: {q_text[:800]}

डेटा सारांश: {df.head(10).to_string()}

कृपया एक संक्षिप्त, औपचारिक उत्तर दें (200-300 शब्द)।"""
        
        try:
            res = ollama.generate(
                model='llama3.2', 
                prompt=prompt,
                options={'temperature': 0.3}
            )
            summary_text = res['response']
        except Exception as e:
            summary_text = f"कुल रिकॉर्ड: {len(df)}\n\n[AI सारांश उपलब्ध नहीं: {str(e)}]"
        
        doc.add_paragraph(summary_text)
        doc.add_paragraph()
        
        # Add data table
        doc.add_heading('परिशिष्ट - डेटा तालिका', level=2)
        
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Light Grid Accent 1'
        
        # Header row
        header_cells = table.rows[0].cells
        for i, col in enumerate(df.columns):
            header_cells[i].text = str(col)
            for paragraph in header_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.size = Pt(10)
        
        # Data rows (limit to 50)
        for idx, row in df.head(50).iterrows():
            row_cells = table.add_row().cells
            for i, val in enumerate(row):
                row_cells[i].text = str(val)[:100]
                for paragraph in row_cells[i].paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
        
        if len(df) > 50:
            doc.add_paragraph(f"\n[नोट: केवल प्रथम 50 रिकॉर्ड दिखाए गए। कुल: {len(df)}]")
        
        # Save
        path = "data/outputs/Vidhan_Sabha_Reply.docx"
        doc.save(path)
        
        return summary_text, path
        
    except Exception as e:
        return f"❌ त्रुटि: {str(e)}", None

# --- Clean UI ---
with gr.Blocks(theme=gr.themes.Soft(), title="Police Document System") as demo:
    gr.Markdown("""
    # 🚔 पुलिस दस्तावेज़ प्रणाली
    ### Document OCR & Report Generation
    *सभी डेटा स्थानीय - कोई बाहरी API नहीं*
    """)
    
    with gr.Tabs():
        # TAB 1: Simple OCR
        with gr.TabItem("📄 दस्तावेज़ OCR"):
            gr.Markdown("""
            ### किसी भी दस्तावेज़ से पाठ निकालें
            FIR, पत्र, रिपोर्ट, या कोई भी हिंदी/अंग्रेजी दस्तावेज़
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    img_in = gr.Image(
                        type="filepath", 
                        label="📸 दस्तावेज़ चित्र अपलोड करें",
                        height=400
                    )
                    btn_ocr = gr.Button(
                        "🔍 पाठ निकालें", 
                        variant="primary", 
                        size="lg"
                    )
                
                with gr.Column(scale=1):
                    gr.Markdown("#### निकाला गया पाठ:")
                    cleaned_output = gr.TextArea(
                        label="✅ साफ पाठ (AI Cleaned)",
                        lines=15,
                        placeholder="यहाँ साफ पाठ दिखाई देगा..."
                    )
            
            with gr.Accordion("🔍 मूल OCR पाठ देखें (Raw)", open=False):
                raw_output = gr.TextArea(
                    label="Raw OCR Output",
                    lines=10,
                    placeholder="मूल OCR आउटपुट..."
                )
            
            btn_ocr.click(
                extract_text_from_image, 
                inputs=img_in, 
                outputs=[raw_output, cleaned_output]
            )
            
            gr.Markdown("""
            ---
            **💡 टिप्स:**
            - स्पष्ट, उच्च रिज़ॉल्यूशन चित्र उपयोग करें
            - अच्छी रोशनी में ली गई फोटो बेहतर काम करती है
            - टेढ़े चित्र को सिस्टम स्वतः सीधा कर देता है
            """)

        # TAB 2: Vidhan Sabha Reports
        with gr.TabItem("📊 विधान सभा रिपोर्ट"):
            gr.Markdown("""
            ### स्वचालित रिपोर्ट जनरेशन
            Excel डेटा और PDF प्रश्नों से औपचारिक उत्तर बनाएं
            """)
            
            with gr.Row():
                ex_in = gr.File(
                    label="📊 Crime Data (Excel)", 
                    file_types=[".xlsx", ".xls"]
                )
                pdf_in = gr.File(
                    label="📄 Questions (PDF)", 
                    file_types=[".pdf"]
                )
            
            btn_generate = gr.Button(
                "📝 रिपोर्ट बनाएं", 
                variant="primary", 
                size="lg"
            )
            
            v_out_txt = gr.TextArea(
                label="रिपोर्ट सारांश",
                lines=10
            )
            v_out_file = gr.File(label="📥 Word डॉक्यूमेंट डाउनलोड करें")
            
            btn_generate.click(
                generate_vidhan_sabha, 
                [ex_in, pdf_in], 
                [v_out_txt, v_out_file]
            )
    
    gr.Markdown("""
    ---
    ### 🔒 सुरक्षा जानकारी:
    ✅ पूर्णतः ऑफलाइन सिस्टम  
    ✅ कोई डेटा बाहर नहीं जाता  
    ✅ स्थानीय Ollama AI का उपयोग  
    ✅ हिंदी और अंग्रेजी दोनों support  
    """)

if __name__ == "__main__":
    print("🚔 पुलिस दस्तावेज़ सिस्टम शुरू हो रहा है...")
    print("📍 ब्राउज़र में यहाँ जाएं: http://localhost:7860/")
    
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        share=False,
        inbrowser=True
    )