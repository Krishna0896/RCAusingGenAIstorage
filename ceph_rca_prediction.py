import subprocess
import json
import os
import requests
from fpdf import FPDF
from datetime import datetime

# ================= CONFIG =================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

PDF_PATH = os.path.expanduser(
    "~/RCAusingGenAIstorage/reports/ceph_rca_latest.pdf"
)

# ================= UTIL =================

def run_cmd(cmd):
    try:
        return subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        return None

# ================= CEPH STATUS =================

def get_ceph_status():
    raw = run_cmd("sudo cephadm shell -- ceph -s --format json")
    if not raw:
        return None

    data = json.loads(raw)

    health = data.get("health", {}).get("status", "UNKNOWN")
    checks = data.get("health", {}).get("checks", {})

    osd_info = data.get("osd", {})
    osds_up = osd_info.get("num_up_osds", 0)
    osds_in = osd_info.get("num_in_osds", 0)

    return {
        "health": health,
        "checks": checks,
        "osds_up": osds_up,
        "osds_in": osds_in
    }

# ================= RCA CLASSIFICATION =================

def classify_incident(status):
    if status["osds_up"] == 0:
        return "TOTAL_OSD_OUTAGE"

    if status["health"] == "HEALTH_WARN":
        if "PG_DEGRADED" in str(status["checks"]).upper():
            return "DEGRADED_REDUNDANCY"
        if "PG_UNDERSIZED" in str(status["checks"]).upper():
            return "REPLICA_MISMATCH"
        return "CAPACITY_OR_CONFIG_RISK"

    if status["health"] == "HEALTH_OK":
        return "NO_INCIDENT"

    return "UNKNOWN_CONDITION"

# ================= GROQ RCA =================

def generate_rca_with_groq(status, incident_type):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a Senior Ceph Storage SRE.

Generate a detailed Root Cause Analysis with ALL sections below.

Incident Type: {incident_type}

Ceph Status:
- Health: {status["health"]}
- OSDs Up: {status["osds_up"]}
- OSDs In: {status["osds_in"]}
- Health Checks: {json.dumps(status["checks"], indent=2)}

MANDATORY SECTIONS:
1. Summary
2. Root Cause
3. Impact Analysis
4. Immediate Remediation Steps
5. Risk & Failure Prediction
6. Long-term Preventive Actions
"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response = r.json()
    except Exception:
        response = {}

    # ✅ VALID RESPONSE
    if "choices" in response and response["choices"]:
        return response["choices"][0]["message"]["content"]

    # ❗ FALLBACK RCA (SAFE, CORRECT, STRUCTURED)
    return generate_fallback_rca(status, incident_type)


def generate_fallback_rca(status, incident_type):
    return f"""
1. Summary
The Ceph cluster is currently in a {status["health"]} state. Automated RCA generation via AI
was unavailable at the time of analysis, so a deterministic fallback RCA was generated.

2. Root Cause
Based on cluster telemetry, the incident type is classified as: {incident_type}.
The primary contributing factor is related to Ceph health checks and OSD availability.

3. Impact Analysis
- OSDs Up: {status["osds_up"]}
- OSDs In: {status["osds_in"]}
- Potential impact includes reduced redundancy or availability depending on workload.

4. Immediate Remediation Steps
- Verify OSD daemon status using `ceph orch ps`
- Check disk availability and OSD provisioning
- Validate Ceph health warnings using `ceph health detail`

5. Risk & Failure Prediction
Failure Risk Level: MEDIUM to HIGH  
If corrective actions are not taken, the cluster may experience degraded redundancy
or service disruption.

6. Long-term Preventive Actions
- Ensure minimum OSD count matches pool replica size
- Implement continuous monitoring with Prometheus alerts
- Automate RCA execution with scheduled background jobs
- Periodically validate OSD disk health and provisioning
"""



# ================= PDF =================

def generate_pdf_report(text):
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    pdf.multi_cell(0, 8, text)
    pdf.output(PDF_PATH)

# ================= MAIN =================

def main():
    print("[1] Checking Ceph status...")
    status = get_ceph_status()

    if not status:
        print("❌ Unable to fetch Ceph status")
        return

    print("[2] Classifying incident...")
    incident_type = classify_incident(status)

    print("[3] Generating RCA using Groq AI...")
    rca_text = generate_rca_with_groq(status, incident_type)

    print("[4] Writing RCA PDF...")
    generate_pdf_report(rca_text)

    print(f"✅ RCA generated: {PDF_PATH}")

if __name__ == "__main__":
    main()
