import requests
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ===============================
# CONFIG
# ===============================
PROMETHEUS_URL = "http://localhost:9090"
PDF_FILE = "Ceph_RCA_Report.pdf"

# ===============================
# PROMETHEUS QUERY FUNCTION
# ===============================
def query_prometheus(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    r = requests.get(url, params={"query": query}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data["status"] == "success" and data["data"]["result"]:
        return float(data["data"]["result"][0]["value"][1])
    return 0

# ===============================
# COLLECT CEPH METRICS
# ===============================
def collect_ceph_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")

    metrics = {
        "cluster_health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_down": query_prometheus("ceph_pg_down"),
    }

    return metrics

# ===============================
# RCA LOGIC
# ===============================
def generate_root_cause(metrics):
    causes = []

    if metrics["cluster_health"] != 1:
        causes.append("Ceph cluster is reporting HEALTH_WARN or HEALTH_ERR")

    if metrics["osd_up"] < metrics["osd_in"]:
        causes.append("One or more OSDs are down")

    if metrics["pg_degraded"] > 0:
        causes.append("Placement Groups are in degraded state")

    if metrics["pg_down"] > 0:
        causes.append("One or more Placement Groups are down")

    if not causes:
        causes.append("No anomalies detected in Ceph cluster")

    return causes

# ===============================
# IMPACT & ACTIONS
# ===============================
def derive_impact_and_actions(metrics):
    impact = []
    immediate = []
    preventive = []

    if metrics["cluster_health"] != 1:
        impact.append("Potential SLA breach and reduced cluster reliability")
        immediate.append("Investigate Ceph health warnings immediately")
        preventive.append("Enable proactive health alerts and capacity monitoring")

    if metrics["osd_up"] < metrics["osd_in"]:
        impact.append("Reduced data redundancy and higher data loss risk")
        immediate.append("Restart or replace the failed OSD")
        preventive.append("Implement disk health checks and predictive failure analysis")

    if metrics["pg_degraded"] > 0:
        impact.append("I/O performance degradation for applications")
        immediate.append("Allow PG recovery and monitor backfill progress")
        preventive.append("Tune recovery limits and add OSD capacity")

    if not impact:
        impact.append("No customer-visible impact detected")
        immediate.append("No immediate remediation required")
        preventive.append("Continue standard monitoring and audits")

    return impact, immediate, preventive

# ===============================
# FAILURE PREDICTION
# ===============================
def predict_failure(metrics):
    score = 0

    if metrics["cluster_health"] != 1:
        score += 2
    if metrics["osd_up"] < metrics["osd_in"]:
        score += 2
    if metrics["pg_degraded"] > 0:
        score += 1

    if score >= 4:
        return "HIGH RISK"
    elif score >= 2:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"

# ===============================
# PDF GENERATION
# ===============================
def generate_pdf(metrics, root_causes, impact, immediate, preventive, risk):
    print("[4] Generating RCA PDF report...")

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Ceph Storage RCA Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Generated:</b> {datetime.now()}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Cluster Metrics</b>", styles["Heading2"]))
    for k, v in metrics.items():
        story.append(Paragraph(f"{k}: {v}", styles["Normal"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Root Cause Analysis</b>", styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(c, styles["Normal"])) for c in root_causes]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Impact</b>", styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(i, styles["Normal"])) for i in impact]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Immediate Remediation</b>", styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(i, styles["Normal"])) for i in immediate]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Long-Term Preventive Actions</b>", styles["Heading2"]))
    story.append(ListFlowable([ListItem(Paragraph(p, styles["Normal"])) for p in preventive]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Failure Risk Prediction</b>", styles["Heading2"]))
    story.append(Paragraph(risk, styles["Normal"]))

    doc = SimpleDocTemplate(PDF_FILE, pagesize=A4)
    doc.build(story)

    print(f"✅ PDF generated: {PDF_FILE}")

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    metrics = collect_ceph_metrics()

    root_causes = generate_root_cause(metrics)
    impact, immediate, preventive = derive_impact_and_actions(metrics)
    risk = predict_failure(metrics)

    generate_pdf(metrics, root_causes, impact, immediate, preventive, risk)

    print("\n===== RCA SUMMARY =====")
    print("Root Cause:", root_causes)
    print("Impact:", impact)
    print("Immediate Action:", immediate)
    print("Preventive Action:", preventive)
    print("Failure Risk:", risk)
