import os
import requests
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ===============================
# CONFIGURATION
# ===============================
PROMETHEUS_URL = "http://localhost:9090"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")   # 🔐 SAFE
PDF_REPORT = "Ceph_RCA_Final_Report.pdf"

if not GROQ_API_KEY:
    raise EnvironmentError("❌ GROQ_API_KEY environment variable not set")

# ===============================
# STEP 1: COLLECT METRICS
# ===============================
def query_prometheus(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    r = requests.get(url, params={"query": query}, timeout=10)
    r.raise_for_status()
    result = r.json()["data"]["result"]
    return result[0]["value"][1] if result else "0"


def collect_ceph_metrics():
    metrics = {
        "cluster_health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status")
    }
    return metrics

def generate_rca_with_groq(metrics):
    prompt = f"""
You are a Ceph Storage Expert.

Cluster Metrics:
- Cluster Health: {metrics.get('cluster_health')}
- OSDs Up: {metrics.get('osd_up')}
- OSDs In: {metrics.get('osd_in')}
- MON Quorum: {metrics.get('mon_quorum')}

Provide Root Cause Analysis and remediation steps.
"""
    # Groq API call continues...

# ===============================
# STEP 2: GROQ RCA GENERATION
# ===============================



    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are an expert Ceph SRE."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )

    data = response.json()

    if "choices" in data:
        return data["choices"][0]["message"]["content"]

    raise Exception(f"Unexpected Groq response: {data}")

# ===============================
# STEP 3: FAILURE PREDICTION
# ===============================


# ===============================
# STEP 4: PDF GENERATION
# ===============================def predict_failure(metrics):
    risk_score = 0
    reasons = []

    if float(metrics["cluster_health"]) != 1:
        risk_score += 50
        reasons.append("Cluster health is not OK")

    if float(metrics["osd_up"]) < float(metrics["osd_in"]):
        risk_score += 30
        reasons.append("Some OSDs are down")

    if float(metrics["mon_quorum"]) != 1:
        risk_score += 20
        reasons.append("Monitor quorum issue")

    risk_level = (
        "LOW" if risk_score < 30 else
        "MEDIUM" if risk_score < 60 else
        "HIGH"
    )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reasons": reasons
    }

def generate_pdf(rca, prediction, metrics):
    print("[4] Generating RCA PDF report...")

    doc = SimpleDocTemplate(PDF_REPORT)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>Ceph RCA & Failure Prediction Report</b>", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"<b>Date:</b> {datetime.now()}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("<b>Cluster Metrics</b>", styles["Heading2"]))
    content.append(Paragraph(f"<pre>{metrics}</pre>", styles["Code"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("<b>Root Cause Analysis</b>", styles["Heading2"]))
    content.append(Paragraph(rca.replace("\n", "<br/>"), styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("<b>Failure Prediction</b>", styles["Heading2"]))
    content.append(Paragraph(prediction.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(content)
    print(f"✅ PDF Generated: {PDF_REPORT}")

# ===============================
# MAIN EXECUTION
# ===============================
if __name__ == "__main__":
    metrics = collect_ceph_metrics()
    rca_text = generate_rca_with_groq(metrics)
    prediction_text = predict_failure(metrics)
    generate_pdf(rca_text, prediction_text, metrics)
