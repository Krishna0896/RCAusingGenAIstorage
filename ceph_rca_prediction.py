#!/usr/bin/env python3

import os
import json
import requests
import subprocess
from datetime import datetime
from fpdf import FPDF

# =========================
# CONFIGURATION
# =========================

PROMETHEUS_URL = "http://localhost:9095/api/v1/query"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

REPORTS_DIR = os.path.expanduser("~/RCAusingGenAIstorage/reports")
PDF_PATH = os.path.join(REPORTS_DIR, "ceph_rca_latest.pdf")

MODEL = "llama-3.1-8b-instant"

# =========================
# UTILITIES
# =========================

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except subprocess.CalledProcessError:
        return ""

# =========================
# CEPH HEALTH CHECK
# =========================

def get_ceph_status():
    raw = run_cmd("sudo cephadm shell -- ceph -s --format json")
    if not raw:
        return None

    data = json.loads(raw)

    health = data.get("health", {}).get("status", "UNKNOWN")
    warnings = data.get("health", {}).get("checks", {})

    osd_info = data.get("osd", {})
    osds_up = osd_info.get("num_up_osds", 0)
    osds_in = osd_info.get("num_in_osds", 0)

    return {
        "health": health,
        "osds_up": osds_up,
        "osds_in": osds_in,
        "warnings": warnings
    }



# =========================
# PROMETHEUS METRICS
# =========================

def query_prometheus(query):
    try:
        r = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=5)
        r.raise_for_status()
        return r.json()["data"]["result"]
    except Exception:
        return None

def collect_metrics():
    metrics = {}

    metrics["osd_up"] = query_prometheus("ceph_osd_up")
    metrics["pg_undersized"] = query_prometheus("ceph_pg_undersized")
    metrics["pg_inactive"] = query_prometheus("ceph_pg_inactive")

    return metrics

# =========================
# RCA CLASSIFICATION LOGIC
# =========================

def classify_issue(status, metrics):
    health = status["health"]
    osds_up = status["osds_up"]
    osds_in = status["osds_in"]

    if health == "HEALTH_OK":
        return "NO_RCA", "Cluster is healthy."

    if health == "HEALTH_WARN":
        if osds_up > 0 and osds_up == osds_in:
            return "CONFIG_WARNING", "Cluster operational with configuration warnings."
        else:
            return "DEGRADED", "Partial OSD availability causing degradation."

    if health == "HEALTH_ERR":
        return "CRITICAL_FAILURE", "Cluster in error state."

    return "UNKNOWN", "Unable to classify cluster state."

# =========================
# GROQ RCA GENERATION (CONTROLLED)
# =========================

def generate_rca_with_groq(rca_type, status, metrics):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a senior Ceph SRE.

STRICT RULES:
- Do NOT invent outages
- Do NOT claim data loss unless stated
- If OSDs are UP, cluster is operational
- HEALTH_WARN is NOT failure
- Only explain the classified RCA

RCA TYPE: {rca_type}

CEPH STATUS:
{json.dumps(status, indent=2)}

PROMETHEUS METRICS:
{json.dumps(metrics, indent=2)}

Generate:
1. Root Cause
2. Impact
3. Evidence
4. Recommendation
"""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    data = r.json()

    if "choices" not in data:
        return "RCA generation failed: invalid LLM response."

    return data["choices"][0]["message"]["content"]

# =========================
# PDF REPORT
# =========================

def generate_pdf_report(rca_text, rca_type):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Ceph RCA Report", ln=True)

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Generated: {datetime.now()}", ln=True)
    pdf.cell(0, 8, f"RCA Type: {rca_type}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "", 11)
    for line in rca_text.split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf.output(PDF_PATH)

# =========================
# MAIN
# =========================

def main():
    print("[1] Checking Ceph status...")
    status = get_ceph_status()

    if not status:
        print("❌ Unable to fetch Ceph status.")
        return

    print("[2] Collecting Prometheus metrics...")
    metrics = collect_metrics()

    rca_type, decision = classify_issue(status, metrics)

    print(f"[3] RCA Decision: {rca_type}")

    if rca_type == "NO_RCA":
        print("✅ Cluster healthy. No RCA generated.")
        return

    print("[4] Generating controlled RCA...")
    rca_text = generate_rca_with_groq(rca_type, status, metrics)

    print("[5] Writing PDF report...")
    generate_pdf_report(rca_text, rca_type)

    print(f"✅ RCA generated: {PDF_PATH}")

if __name__ == "__main__":
    main()
