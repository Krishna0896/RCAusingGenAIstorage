#!/usr/bin/env python3

import os
import requests
from fpdf import FPDF
from datetime import datetime

# =========================
# CONFIGURATION
# =========================

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY environment variable not set")

BASE_DIR = os.path.expanduser("~/RCAusingGenAIstorage")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PDF_PATH = os.path.join(REPORTS_DIR, "Ceph_RCA_Report.pdf")

# =========================
# PROMETHEUS HELPERS
# =========================

def query_prometheus(metric):
    try:
        r = requests.get(
            PROMETHEUS_URL,
            params={"query": metric},
            timeout=5
        )
        result = r.json()["data"]["result"]
        if not result:
            return 0
        return float(result[0]["value"][1])
    except Exception:
        return 0

def collect_ceph_metrics():
    metrics = {
        "ceph_health_status": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status"),
    }
    return metrics

# =========================
# GROQ RCA GENERATION
# =========================

def generate_rca_with_groq(metrics):
    prompt = f"""
You are a senior Ceph Storage SRE.

Generate a **DETAILED Root Cause Analysis (RCA)** with the following sections:

1. Root Cause Analysis
2. Impact
3. Immediate Remediation (step-by-step commands)
4. Long-term Preventive Actions
5. Failure Prediction
   - Risk Level
   - Reasons
   - Estimated Time to Impact

Ceph Metrics:
- ceph_health_status: {metrics['ceph_health_status']}
- osd_up: {metrics['osd_up']}
- osd_in: {metrics['osd_in']}
- pg_degraded: {metrics['pg_degraded']}
- pg_undersized: {metrics['pg_undersized']}
- mon_quorum: {metrics['mon_quorum']}

Important rules:
- Even ONE OSD down must be treated as HIGH RISK
- Be explicit and professional
- Suitable for senior management review
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You generate enterprise-grade storage RCA reports."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()

    response = r.json()

    # ✅ Robust parsing (fixes 'choices' error)
    return response.get("choices", [{}])[0].get("message", {}).get("content", "RCA generation failed.")

# =========================
# PDF GENERATION
# =========================

def generate_pdf_report(rca_text):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    pdf.multi_cell(0, 8, rca_text)

    # ✅ Always overwrite
    pdf.output(PDF_PATH)

    print(f"✅ RCA PDF updated: {PDF_PATH}")

# =========================
# MAIN
# =========================

def main():
    print("[1] Collecting Ceph metrics from Prometheus...")
    metrics = collect_ceph_metrics()

    print("[2] Generating RCA using Groq AI...")
    rca_text = generate_rca_with_groq(metrics)

    print("[3] Writing RCA PDF...")
    generate_pdf_report(rca_text)

    print("🎯 RCA generation completed successfully")

if __name__ == "__main__":
    main()
