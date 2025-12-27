import os
import subprocess
import requests
from datetime import datetime
from fpdf import FPDF

# Groq AI configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.ai/v1/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# PDF export path
PDF_PATH = "/home/krishna/RCAusingGenAIstorage/reports/Ceph_RCA_Report.pdf"

def get_ceph_status():
    """Collect Ceph cluster facts"""
    try:
        result = subprocess.run(
            ["sudo", "ceph", "status", "--format", "json-pretty"],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[❌] Unable to fetch Ceph status: {e}")
        return "Unable to collect Ceph facts."

def query_groq_ai(prompt):
    """Query Groq AI for RCA or prediction"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": GROQ_MODEL,
        "prompt": prompt,
        "max_tokens": 600,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            return "[Groq AI did not return a valid response]"
    except Exception as e:
        return f"[Error querying Groq AI: {e}]"

def generate_pdf_report(ceph_facts, rca_text, impact_text, remediation_text, preventive_text, prediction_text):
    """Generate structured PDF report"""
    reports_dir = os.path.dirname(PDF_PATH)
    os.makedirs(reports_dir, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ceph RCA & Predictive Analysis Report", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Generated at: {datetime.now()}", ln=True)
    pdf.cell(0, 8, f"AI Model Used: {GROQ_MODEL}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Ceph Cluster Facts", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, ceph_facts)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Root Cause Analysis (RCA)", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, rca_text)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Impact", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, impact_text)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Immediate Remediation Steps", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, remediation_text)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Long-Term Preventive Actions", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, preventive_text)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Predictive Analysis", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, prediction_text)

    pdf.output(PDF_PATH)
    print(f"✅ PDF generated: {PDF_PATH}")

def main():
    print("[1] Collecting Ceph cluster facts...")
    ceph_facts = get_ceph_status()

    print("[2] Generating RCA using Groq AI...")
    rca_prompt = f"""
    Analyze the following Ceph cluster status and generate structured RCA.
    Include:
    1. Root Cause
    2. Impact
    3. Immediate Remediation Steps
    4. Long-Term Preventive Actions

    Ceph Status:
    {ceph_facts}
    """
    rca_full = query_groq_ai(rca_prompt)

    # For simplicity, we assume Groq AI returns a structured response with sections separated.
    # If not, you could parse by keywords.
    rca_sections = rca_full.split("\n\n")
    rca_text = rca_sections[0] if len(rca_sections) > 0 else "[No RCA provided]"
    impact_text = rca_sections[1] if len(rca_sections) > 1 else "[No Impact provided]"
    remediation_text = rca_sections[2] if len(rca_sections) > 2 else "[No Remediation provided]"
    preventive_text = rca_sections[3] if len(rca_sections) > 3 else "[No Preventive Actions provided]"

    print("[3] Generating Predictive Analysis using Groq AI...")
    prediction_prompt = f"""
    Based on the following Ceph cluster status, predict potential next failures, components at risk,
    and recommend proactive actions. Use structured explanation.

    Ceph Status:
    {ceph_facts}
    """
    prediction_text = query_groq_ai(prediction_prompt)

    print("[4] Exporting PDF report...")
    generate_pdf_report(
        ceph_facts, rca_text, impact_text, remediation_text, preventive_text, prediction_text
    )

if __name__ == "__main__":
    main()
