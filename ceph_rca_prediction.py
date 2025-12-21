import os
import requests
import datetime
from fpdf import FPDF

# ================= CONFIG =================
PROMETHEUS_URL = "http://localhost:9090"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

# ================= PROMETHEUS QUERY =================
def query_prometheus(metric):
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": metric},
            timeout=5
        )
        data = r.json()
        if data["status"] != "success" or not data["data"]["result"]:
            return 0
        return float(data["data"]["result"][0]["value"][1])
    except Exception:
        return 0

def collect_ceph_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    return {
        "ceph_health_status": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status")
    }

# ================= GROQ RCA =================
def generate_rca_with_groq(metrics):
    print("[2] Generating detailed RCA using Groq AI...")

    prompt = (
        "You are a Senior Ceph Storage Reliability Engineer.\n\n"
        "Generate a VERY DETAILED Root Cause Analysis with sections:\n"
        "1. Root Cause Analysis\n"
        "2. Impact\n"
        "3. Immediate Remediation\n"
        "4. Long-term Preventive Actions\n"
        "5. Failure Prediction\n\n"
        f"Metrics:\n"
        f"ceph_health_status={metrics['ceph_health_status']}\n"
        f"osd_up={metrics['osd_up']}\n"
        f"osd_in={metrics['osd_in']}\n"
        f"pg_degraded={metrics['pg_degraded']}\n"
        f"pg_undersized={metrics['pg_undersized']}\n"
        f"mon_quorum={metrics['mon_quorum']}\n\n"
        "RULES:\n"
        "- If ANY OSD is down, Failure Risk MUST be HIGH\n"
        "- Explain each metric clearly\n"
        "- Use bullet points and numbered steps\n"
    )

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
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = r.json()

        if "choices" not in data:
            return "Groq AI error. Raw response:\n" + str(data)

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return "Groq AI exception occurred:\n" + str(e)

# ================= PDF GENERATION =================
def generate_pdf(rca_text):
    print("[4] Generating RCA PDF report...")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Ceph RCA & Failure Prediction Report", ln=True)

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Generated on: {datetime.datetime.now()}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "", 11)
    for line in rca_text.split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf.output("Ceph_RCA_Report.pdf")
    print("✅ PDF generated: Ceph_RCA_Report.pdf")

# ================= MAIN =================
if __name__ == "__main__":
    metrics = collect_ceph_metrics()
    rca_text = generate_rca_with_groq(metrics)
    generate_pdf(rca_text)

    print("\n===== RCA OUTPUT =====\n")
    print(rca_text)
