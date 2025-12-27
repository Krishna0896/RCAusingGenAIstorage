#!/usr/bin/env python3
import os
import json
import subprocess
import requests
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

PDF_PATH = "/home/krishna/RCAusingGenAIstorage/reports/Ceph_RCA_Report.pdf"

PROMETHEUS_URL = "http://localhost:9095/api/v1/query"
# ==========================================


def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out
    except subprocess.CalledProcessError as e:
        return None


def get_ceph_status():
    cmd = "sudo cephadm shell -- ceph -s -f json"
    try:
        output = subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.STDOUT,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("❌ Failed to run ceph command")
        print(e.output)
        return None

    # 🔴 cephadm prints noise before JSON — strip it
    json_start = output.find("{")
    if json_start == -1:
        print("❌ No JSON found in ceph output")
        print(output)
        return None

    json_text = output[json_start:]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed")
        print(json_text)
        return None



def extract_ceph_facts(status):
    facts = {}

    health = status.get("health", {})
    facts["health_status"] = health.get("status", "UNKNOWN")
    facts["health_checks"] = list(health.get("checks", {}).keys())

    osdmap = status.get("osdmap", {}).get("osdmap", {})
    facts["osds_total"] = osdmap.get("num_osds", 0)
    facts["osds_up"] = osdmap.get("num_up_osds", 0)
    facts["osds_in"] = osdmap.get("num_in_osds", 0)

    pgmap = status.get("pgmap", {})
    facts["pg_states"] = pgmap.get("pgs_by_state", [])
    facts["degraded_objects"] = pgmap.get("degraded_objects", 0)

    return facts


def query_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior Ceph storage SRE generating accurate RCA reports."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def generate_ai_rca(facts):
    prompt = f"""
Ceph Cluster Facts:
- Health: {facts['health_status']}
- OSDs Total: {facts['osds_total']}
- OSDs Up: {facts['osds_up']}
- OSDs In: {facts['osds_in']}
- Health Checks: {facts['health_checks']}
- Degraded Objects: {facts['degraded_objects']}

Generate:
1. Root Cause Analysis
2. Impact
3. Immediate Remediation Steps
4. Long-Term Preventive Actions
5. Predictive Analysis (next likely failure if no action taken)

IMPORTANT:
- Do NOT claim total OSD failure unless osds_up == 0
- Be technically precise
- No assumptions
"""

    ai_text = query_groq(prompt)

    if ai_text:
        return ai_text

    # -------- SAFE FALLBACK (NO AI) --------
    return f"""
Root Cause Analysis:
The cluster is in {facts['health_status']} state due to insufficient data redundancy or replica configuration mismatch.
OSDs are present and operational; this is not a total OSD failure.

Impact:
Reduced fault tolerance. Data availability is maintained but resilience is compromised.

Immediate Remediation:
- Adjust pool replica size to match available OSDs
- Verify OSD placement and recovery status

Long-Term Preventive Actions:
- Maintain minimum 3 OSDs for production clusters
- Add capacity monitoring and alerts

Predictive Analysis:
If current redundancy remains unchanged, future OSD failure may lead to data unavailability.
"""


def generate_pdf(facts, rca_text):
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)

    doc = SimpleDocTemplate(PDF_PATH)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Ceph RCA Report</b>", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now()}", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(Paragraph("<b>Cluster Summary</b>", styles["Heading2"]))
    for k, v in facts.items():
        story.append(Paragraph(f"{k}: {v}", styles["Normal"]))

    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(Paragraph("<b>AI Generated RCA</b>", styles["Heading2"]))
    for line in rca_text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)


def main():
    print("[1] Reading Ceph cluster state...")
    status = get_ceph_status()
    if not status:
        print("❌ Unable to read Ceph status")
        return

    facts = extract_ceph_facts(status)

    print("[2] Generating RCA using Groq AI...")
    rca_text = generate_ai_rca(facts)

    print("[3] Generating PDF report...")
    generate_pdf(facts, rca_text)

    print(f"✅ RCA report generated: {PDF_PATH}")


if __name__ == "__main__":
    main()
