import os
import requests
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# -------------------------------
# CONFIG
# -------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "REPLACE_WITH_YOUR_GROQ_KEY")
GROQ_MODEL = "llama3-70b-8192"

PDF_OUTPUT = "Ceph_RCA_Final_Report.pdf"

# -------------------------------
# STEP 1: COLLECT METRICS
# (Replace with real Prometheus queries later)
# -------------------------------
def collect_ceph_metrics():
    """
    Mocked metrics based on your real cluster output.
    Replace this with Prometheus API calls later.
    """
    return {
        "cluster_health": "HEALTH_WARN",
        "osd_up": 0,
        "osd_total": 1,
        "pgs_degraded": 10,
        "pgs_undersized": 80,
        "objects_degraded_pct": 50,
        "disk_used_gb": 0.29,
        "disk_total_gb": 100,
        "mon_quorum": True,
        "timestamp": datetime.now().isoformat()
    }

# -------------------------------
# STEP 2: GROQ RCA GENERATION
# -------------------------------
def generate_rca_with_groq(metrics):
    prompt = f"""
You are a senior Ceph Storage SRE.

Analyze the following Ceph cluster metrics and generate a Root Cause Analysis.

Metrics:
- Cluster Health: {metrics['cluster_health']}
- OSDs Up: {metrics['osd_up']} / {metrics['osd_total']}
- PGs Degraded: {metrics['pgs_degraded']}
- PGs Undersized: {metrics['pgs_undersized']}
- Degraded Objects (%): {metrics['objects_degraded_pct']}
- Disk Usage: {metrics['disk_used_gb']}GB / {metrics['disk_total_gb']}GB
- MON Quorum: {metrics['mon_quorum']}

Provide:
1. Root Cause
2. Contributing Factors
3. Impact
4. Immediate Remediation
5. Long-term Prevention
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=60
    )

    return response.json()["choices"][0]["message"]["content"]

# -------------------------------
# STEP 3: FAILURE PREDICTION
# -------------------------------
def predict_failure(metrics):
    if metrics["osd_up"] == 0:
        risk = "CRITICAL"
        prediction = (
            "If the OSD remains down, the cluster will enter complete data "
            "unavailability. Any additional failure will cause total outage."
        )
    elif metrics["objects_degraded_pct"] > 30:
        risk = "HIGH"
        prediction = "High probability of service degradation within 24–48 hours."
    else:
        risk = "LOW"
        prediction = "Cluster is stable with no immediate failure risk."

    return risk, prediction

# -------------------------------
# STEP 4: PDF GENERATION
# -------------------------------
def generate_pdf(metrics, rca_text, risk, prediction):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(PDF_OUTPUT, pagesize=A4)
    story = []

    story.append(Paragraph("<b>Ceph Storage Cluster – RCA & Prediction Report</b>", styles["Title"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>Report Timestamp:</b> " + metrics["timestamp"], styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # Cluster Summary Table
    table_data = [
        ["Metric", "Value"],
        ["Cluster Health", metrics["cluster_health"]],
        ["OSDs Up", f"{metrics['osd_up']} / {metrics['osd_total']}"],
        ["PGs Degraded", metrics["pgs_degraded"]],
        ["PGs Undersized", metrics["pgs_undersized"]],
        ["Degraded Objects (%)", metrics["objects_degraded_pct"]],
        ["Disk Usage", f"{metrics['disk_used_gb']}GB / {metrics['disk_total_gb']}GB"],
        ["MON Quorum", metrics["mon_quorum"]],
    ]

    story.append(Table(table_data, hAlign="LEFT"))
    story.append(Spacer(1, 0.3 * inch))

    # RCA Section
    story.append(Paragraph("<b>Root Cause Analysis (AI Generated)</b>", styles["Heading2"]))
    for line in rca_text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Prediction Section
    story.append(Paragraph("<b>Failure Prediction</b>", styles["Heading2"]))
    story.append(Paragraph(f"<b>Risk Level:</b> {risk}", styles["Normal"]))
    story.append(Paragraph(f"<b>Prediction:</b> {prediction}", styles["Normal"]))

    doc.build(story)

# -------------------------------
# MAIN EXECUTION
# -------------------------------
if __name__ == "__main__":
    print("[1] Collecting Ceph metrics...")
    metrics = collect_ceph_metrics()

    print("[2] Generating RCA using Groq...")
    rca_text = generate_rca_with_groq(metrics)

    print("[3] Predicting failure risk...")
    risk, prediction = predict_failure(metrics)

    print("[4] Generating PDF report...")
    generate_pdf(metrics, rca_text, risk, prediction)

    print(f"\n✅ RCA PDF Generated Successfully: {PDF_OUTPUT}")
