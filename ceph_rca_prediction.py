import os
import requests
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------- CONFIG ----------------
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"
PDF_FILE = "Ceph_RCA_Report.pdf"

# ------------- PROMETHEUS QUERY ----------
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

def collect_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    return {
        "ceph_health_status": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status")
    }

# ------------- GROQ RCA GENERATION ----------
def generate_rca_with_groq(metrics):
    print("[2] Generating detailed RCA using Groq AI...")

    prompt = f"""
def generate_rca_with_groq(metrics):
    print("[2] Generating detailed RCA using Groq AI...")

    prompt = f"""
You are a Senior Ceph Storage Reliability Engineer.

Generate a detailed Root Cause Analysis with:
- Root Cause Analysis
- Impact
- Immediate Remediation
- Long-term Preventive Actions
- Failure Prediction

Metrics:
ceph_health_status={metrics['ceph_health_status']}
osd_up={metrics['osd_up']}
osd_in={metrics['osd_in']}
pg_degraded={metrics['pg_degraded']}
pg_undersized={metrics['pg_undersized']}
mon_quorum={metrics['mon_quorum']}

RULE:
- If any OSD is down, risk MUST be HIGH
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        data = response.json()

        # 🔥 CRITICAL FIX
        if "choices" not in data:
            return f"""
Root Cause Analysis
Groq AI failed to generate RCA.

Raw response received:
{data}

Likely Causes:
- Invalid or missing GROQ_API_KEY
- API rate limit exceeded
- Network connectivity issue

Impact
RCA generation unavailable, but Ceph metrics indicate potential risk.

Immediate Remediation
1. Validate GROQ_API_KEY
2. Check network access
3. Retry request

Failure Prediction
Failure Risk Level: HIGH
Reason: OSD down detected but LLM unavailable
"""

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"""
Root Cause Analysis
Groq AI exception occurred.

Error:
{str(e)}

Impact
Automated RCA unavailable.

Immediate Remediation
Check Groq API connectivity and credentials.

Failure Prediction
Failure Risk Level: HIGH
Reason: OSD down with RCA generation failure
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    return r.json()["choices"][0]["message"]["content"]

# ------------- PDF GENERATION ----------
def generate_pdf(rca_text):
    print("[3] Generating RCA PDF report...")
    c = canvas.Canvas(PDF_FILE, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Ceph RCA & Failure Prediction Report")

    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Generated on: {datetime.datetime.now()}")

    y -= 30
    c.setFont("Helvetica", 10)

    for line in rca_text.split("\n"):
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 10)
        c.drawString(40, y, line)
        y -= 14

    c.save()
    print(f"✅ PDF generated: {PDF_FILE}")

# ------------- MAIN ----------
if __name__ == "__main__":
    metrics = collect_metrics()
    rca_text = generate_rca_with_groq(metrics)
    generate_pdf(rca_text)

    print("\n===== RCA OUTPUT =====\n")
    print(rca_text)
