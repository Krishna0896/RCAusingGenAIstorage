import os
import subprocess
import requests
from datetime import datetime
from fpdf import FPDF

# Your Groq API key (ensure it's set in environment)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.ai/v1/completions"  # Groq API endpoint

# Use LLaMA 3.1 model
GROQ_MODEL = "llama-3.1-8b-instant"

PDF_PATH = "/home/krishna/RCAusingGenAIstorage/reports/Ceph_RCA_Report.pdf"

def get_ceph_status():
    """Collect Ceph cluster facts"""
    try:
        result = subprocess.run(
            ["sudo", "ceph", "status", "--format", "json"],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[❌] Unable to fetch Ceph status: {e}")
        return None

def query_groq_ai(prompt):
    """Query Groq AI for RCA or predictive analysis"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": GROQ_MODEL,
        "prompt": prompt,
        "max_tokens": 500,
    }
    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        response = r.json()
        if "choices" in response:
            return response["choices"][0]["message"]["content"]
        else:
            return "[Groq AI did not return a valid response]"
    except Exception as e:
        return f"[Error querying Groq AI: {e}]"

def generate_pdf_report(ceph_facts, rca_text, prediction_text):
    """Generate RCA + predictive analysis PDF"""
    reports_dir = os.path.dirname(PDF_PATH)
    os.makedirs(reports_dir, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ceph RCA & Predictive Report (Groq AI - LLaMA 3.1)", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Generated at: {datetime.now()}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Ceph Cluster Facts", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, ceph_facts)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Generated RCA", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, rca_text)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Predictive Analysis", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, prediction_text)

    pdf.output(PDF_PATH)
    print(f"✅ RCA & Predictive PDF generated: {PDF_PATH}")

def main():
    print("[1] Collecting Ceph cluster facts...")
    ceph_facts = get_ceph_status()
    if not ceph_facts:
        ceph_facts = "Unable to collect Ceph facts."

    print("[2] Generating RCA using Groq AI (LLaMA 3.1)...")
    rca_prompt = f"Analyze the following Ceph cluster status and provide a detailed RCA including root cause, impact, immediate remediation, long-term preventive actions:\n{ceph_facts}"
    rca_text = query_groq_ai(rca_prompt)

    print("[3] Generating predictive analysis using Groq AI (LLaMA 3.1)...")
    prediction_prompt = f"Based on the following Ceph cluster status, predict potential next failures, which components are at risk, and suggest proactive measures:\n{ceph_facts}"
    prediction_text = query_groq_ai(prediction_prompt)

    print("[4] Exporting RCA & predictive analysis to PDF...")
    generate_pdf_report(ceph_facts, rca_text, prediction_text)

if __name__ == "__main__":
    main()
