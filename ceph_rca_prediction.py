#!/usr/bin/env python3

import subprocess
import json
import os
import datetime
from groq import Groq
from fpdf import FPDF

# ==============================
# CONFIGURATION
# ==============================

PDF_PATH = "/home/krishna/RCAusingGenAIstorage/reports/Ceph_RCA_Report.pdf"
GROQ_MODEL = "llama-3.1-8b-instant"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ==============================
# CEph DATA COLLECTION
# ==============================

def run_cmd(cmd):
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def get_ceph_status():
    output = run_cmd("sudo cephadm shell -- ceph -s -f json")
    return json.loads(output)


def get_osd_status():
    output = run_cmd("sudo cephadm shell -- ceph osd stat -f json")
    return json.loads(output)


def get_pg_status():
    output = run_cmd("sudo cephadm shell -- ceph pg stat -f json")
    return output


def collect_ceph_facts():
    status = get_ceph_status()
    osd_stat = get_osd_status()
    pg_stat = get_pg_status()

    facts = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "cluster_health": status["health"]["status"],
        "health_checks": list(status["health"]["checks"].keys())
            if "checks" in status["health"] else [],
        "osd_summary": {
            "total": osd_stat["num_osds"],
            "up": osd_stat["num_up_osds"],
            "in": osd_stat["num_in_osds"]
        },
        "pg_summary_raw": pg_stat
    }

    return facts

# ==============================
# GROQ AI RCA ENGINE
# ==============================

def generate_rca_with_groq(ceph_facts):
    prompt = f"""
You are a SENIOR Ceph Storage SRE.

Below are VERIFIED FACTS collected LIVE from a Ceph cluster.
DO NOT assume or hallucinate anything.

FACTS (JSON):
{json.dumps(ceph_facts, indent=2)}

INSTRUCTIONS:
- If OSDs are UP, do NOT report OSD outage
- If HEALTH_WARN, explain the exact reason
- Be accurate, conservative, and professional

OUTPUT FORMAT:
1. Incident Summary
2. Root Cause
3. Impact
4. Immediate Remediation
5. Long-Term Preventive Actions
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content

# ==============================
# PDF GENERATION
# ==============================

def generate_pdf_report(ceph_facts, rca_text):
    from fpdf import FPDF
    import os
    from datetime import datetime

    PDF_PATH = "/home/krishna/RCAusingGenAIstorage/reports/Ceph_RCA_Report.pdf"

    # ✅ DEFINE FIRST
    reports_dir = os.path.dirname(PDF_PATH)

    # ✅ THEN USE
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ceph RCA Report (Generated using Groq AI)", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Generated at: {datetime.now()}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Ceph Cluster Facts", ln=True)

    pdf.set_font("Arial", size=10)
    for k, v in ceph_facts.items():
        pdf.multi_cell(0, 6, f"{k}: {v}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Generated RCA", ln=True)

    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, rca_text)

    pdf.output(PDF_PATH)
    print(f"✅ RCA PDF generated: {PDF_PATH}")


# ==============================
# MAIN
# ==============================

def main():
    print("[1] Collecting Ceph cluster facts...")
    ceph_facts = collect_ceph_facts()

    print("[2] Generating RCA using Groq AI...")
    rca_text = generate_rca_with_groq(ceph_facts)

    print("[3] Exporting RCA to PDF...")
    generate_pdf_report(ceph_facts, rca_text)

    print(f"✅ RCA generated successfully:")
    print(f"   {PDF_PATH}")

if __name__ == "__main__":
    main()
