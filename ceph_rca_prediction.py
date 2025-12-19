import os
import requests
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ===============================
# CONFIGURATION
# ===============================
PROMETHEUS_URL = "http://localhost:9095"
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
    return r.json()["data"]["result"]

def collect_ceph_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")

    metrics = {
        "cluster_health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status")
    }

    return json.dumps(metrics, indent=2)

# ===============================
# STEP 2: GROQ RCA GENERATION
# ===============================
def generate_rca_with_groq(metrics):
    print("[2] Generating RCA using Groq LLM...")

    prompt = f"""
You are a senior storage reliability engineer.

Analyze the following Ceph cluster metrics and generate:
1. Root Cause Analysis
2. Impact
3. Recommended Actions
4. Failure Risk Prediction

Metrics:
- Cluster Health: {metrics['cluster_health']}
- OSDs Up: {metrics['osd_up']}
- OSDs In: {metrics['osd_in']}
- Available Capacity (GB): {metrics['available_gb']}
"""


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
def predict_failure(metrics_json):
    print("[3] Predicting failure risk...")

    risk = "LOW"
    reasons = []

    metrics = json.loads(metrics_json)

    for item in metrics.get("osd_up", []):
        if float(item["value"][1]) == 0:
            risk = "HIGH"
            reasons.append("OSD down detected")

    if metrics.get("pg_degraded"):
        risk = "HIGH"
        reasons.append("Degraded PGs present")

    if metrics.get("pg_undersized"):
        risk = "HIGH"
        reasons.append("Undersized PGs detected")

    prediction = f"""
Failure Risk Level: {risk}

Reasons:
- {"; ".join(reasons) if reasons else "No critical issues detected"}

Estimated Time to Impact:
- Immediate to short-term if no action taken
"""

    return prediction

# ===============================
# STEP 4: PDF GENERATION
# ===============================
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
