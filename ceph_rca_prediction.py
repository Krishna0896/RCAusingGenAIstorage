#!/usr/bin/env python3
import os
import requests
from datetime import datetime
from fpdf import FPDF

# ==============================
# CONFIGURATION
# ==============================
PROMETHEUS_URL = "http://127.0.0.1:9090/api/v1/query"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Absolute paths (cron safe)
# ==============================
# ABSOLUTE PDF PATH (CRON SAFE)
# ==============================
HOME_DIR = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME_DIR, "RCAusingGenAIstorage")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(REPORT_DIR, exist_ok=True)

PDF_FILE = os.path.join(
    REPORT_DIR,
    f"Ceph_RCA_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
)

# ==============================
# PROMETHEUS QUERY FUNCTION
# ==============================
def query_prometheus(metric):
    try:
        r = requests.get(
            PROMETHEUS_URL,
            params={"query": metric},
            timeout=10
        )
        data = r.json()["data"]["result"]
        if not data:
            return 0
        return float(data[0]["value"][1])
    except Exception:
        return 0


# ==============================
# COLLECT CEPH METRICS
# ==============================
def collect_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    return {
        "health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status"),
    }


# ==============================
# GROQ RCA GENERATION
# ==============================
def generate_rca_with_groq(metrics):
    print("[2] Generating RCA using Groq AI...")

    prompt = f"""
You are a Senior Storage Reliability Engineer.

Generate a DETAILED Root Cause Analysis for a Ceph cluster issue.

Metrics:
- ceph_health_status: {metrics['health']}
- osd_up: {metrics['osd_up']}
- osd_in: {metrics['osd_in']}
- pg_degraded: {metrics['pg_degraded']}
- pg_undersized: {metrics['pg_undersized']}
- mon_quorum: {metrics['mon_quorum']}

Rules:
- Even if cluster health looks OK, OSD down must be treated as HIGH RISK
- Output must include these sections EXACTLY:

Root Cause Analysis
Impact
Immediate Remediation
Long-term Preventive Actions
Failure Prediction

Failure Prediction must include:
- Risk Level (LOW / MEDIUM / HIGH)
- Reasons
- Estimated Time to Impact
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    return r.json()["choices"][0]["message"]["content"]


# ==============================
# PDF GENERATION
# ==============================
def generate_pdf(rca_text):
    print("[3] Generating RCA PDF report...")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Ceph RCA & Failure Prediction Report", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Generated on: {TIMESTAMP}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    for line in rca_text.split("\n"):
        pdf.multi_cell(0, 6, line)

    pdf.output(PDF_FILE)
    print(f"✅ PDF generated: {PDF_FILE}")


# ==============================
# MAIN
# ==============================
def main():
    metrics = collect_metrics()
    rca_text = generate_rca_with_groq(metrics)
    generate_pdf(rca_text)

    print("\n===== RCA SUMMARY (Console) =====\n")
    print(rca_text)


if __name__ == "__main__":
    main()
