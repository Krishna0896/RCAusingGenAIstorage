import os
import json
import requests
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------- CONFIG ----------------
PROM_URL = "http://127.0.0.1:9090/api/v1/query"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

REPORT_DIR = os.path.expanduser("~/RCAusingGenAIstorage/reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ------------- PROMETHEUS QUERY ----------
def query_prom(query):
    try:
        r = requests.get(PROM_URL, params={"query": query}, timeout=5)
        result = r.json()["data"]["result"]
        if not result:
            return 0
        return int(float(result[0]["value"][1]))
    except Exception:
        return 0

# ------------- METRICS COLLECTION --------
def collect_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    return {
        "ceph_health_status": query_prom("ceph_health_status"),
        "osd_up": query_prom("ceph_osd_up"),
        "pg_degraded": query_prom("ceph_pg_degraded"),
        "pg_undersized": query_prom("ceph_pg_undersized"),
        "mon_quorum": query_prom("ceph_mon_quorum_status"),
    }

# ------------- GROQ RCA GENERATION -------
def generate_rca_with_groq(metrics):
    print("[2] Generating RCA using Groq AI...")

    prompt = f"""
You are a Senior Ceph Storage SRE.

Generate a **DETAILED Root Cause Analysis** with the following sections:

Root Cause Analysis
Impact
Immediate Remediation
Long-term Preventive Actions
Failure Prediction

Ceph Metrics:
- ceph_health_status: {metrics['ceph_health_status']}
- osd_up: {metrics['osd_up']}
- pg_degraded: {metrics['pg_degraded']}
- pg_undersized: {metrics['pg_undersized']}
- mon_quorum: {metrics['mon_quorum']}

Rules:
- If osd_up < 2 → Failure Risk = HIGH
- Write enterprise-grade RCA
- Bullet points + explanations
- Assume management audience
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    response = r.json()

    # ✅ CORRECT GROQ RESPONSE PARSING
    return response["choices"][0]["message"]["content"]

# ------------- PDF GENERATION -------------
def generate_pdf_report(rca_text):
    print("[3] Generating RCA PDF report...")

    reports_dir = os.path.dirname(PDF_PATH)
    os.makedirs(reports_dir, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", size=11)

    for line in rca_text.split("\n"):
        pdf.multi_cell(0, 8, line)

    # 🔥 OVERWRITE SAME FILE EVERY TIME
    pdf.output(PDF_PATH)

    print(f"✅ PDF updated (overwritten): {PDF_PATH}")


# ------------- MAIN ----------------------
def main():
    metrics = collect_metrics()
    rca_text = generate_rca_with_groq(metrics)
    generate_pdf(rca_text)

    print("\n===== RCA SUMMARY (Console) =====\n")
    print(rca_text)

if __name__ == "__main__":
    main()
