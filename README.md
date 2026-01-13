# 👮 Police Intelligence & BI Dashboard (Standalone)

A secure, offline AI decision-support system designed for the Chhattisgarh Police. This system automates Vidhan Sabha reporting, criminal record summarization, and statistical trend analysis without requiring an internet connection.

## 🌟 Key Capabilities

### 1. Dual-Input Intelligence Assistant
A sophisticated reasoning engine that balances user-provided context with pre-trained knowledge.
* **Reply Structure Control**: Select from predefined tones (Legal, Official, Academic) and structures (Pointwise, Paragraph Flowwise).
* **Novel Data Prioritization**: A dedicated field for context-specific data that the AI weighs more heavily than its general training.
* **Multilingual Commands**: Supports inputs in both Hindi and English.

### 2. Statistical BI & Trend Analysis
Automated "Power BI" style reporting for officers without statistical expertise.
* **Dynamic Filtering**: Filter data by **District**, **Police Range**, or **Police Station**.
* **Trend Analysis**: Analyze crime patterns over 1, 3, or 5-year spans.
* **Visual Intelligence**: Generates frequency charts, pie charts, and time-of-day correlation plots.
* **Causal Insight**: Automated identification of basic correlations between variables.

### 3. Vidhan Sabha Automation
* **PDF-to-Draft**: Directly converts parliamentary question PDFs into official "प्रारुप उत्तर" (Draft Answer) format.
* **Excel Integration**: Automatically pulls statistics from complex multi-station Excel sheets to populate reports.

### 4. Advanced Offline OCR
* **Image Cleaning**: Built-in pre-processing to read low-quality or handwritten FIR images.
* **Structured Extraction**: Extracts FIR Number, IPC Sections, Accused details, and Incident dates into organized fields.

---

## 🏗️ System Architecture



- **Model Engine**: Ollama (Running Llama 3.2 3B/8B).
- **OCR Engine**: EasyOCR (Standalone Hindi/English models).
- **Data Engine**: Pandas & Matplotlib (For zero-hallucination statistics).
- **Interface**: Gradio (Local browser-based dashboard).

---

## 🛠️ Installation & Setup (D: Drive)

### 1. Prerequisites
Ensure you have **Ollama** installed and the model downloaded:
```powershell
ollama pull llama3.2
