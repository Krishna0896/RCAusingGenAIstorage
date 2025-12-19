import requests
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------- CONFIG ----------------
PROMETHEUS_URL = "http://localhost:9090"
TIMEOUT = 10
PDF_FILE = "Ceph_RCA_Report.pdf"

# ---------------- PROMETHEUS QUERY ----------------
def query_prometheus(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    try:
        response = requests.get(url, params={"query": query}, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()["data"]["result"]
        if not result:
            return None
        return float(result[0]["value"][1])
    except Exception as e:
        print(f"[ERROR] Prometheus query failed: {query} → {e}")
        return None

# ---------------- METRICS COLLECTION ----------------
def collect_ceph_metrics():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cluster_health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
    }

# ---------------- RCA LOGIC ----------------
def generate_rca(metrics):
    issues = []

    if metrics["cluster_health"] is not None and metrics["cluster_health"] != 1:
        issues.append("Cluster health is WARNING or ERROR")

    if metrics["osd_up"] is not None and metrics["osd_in"] is not None:
        if metrics["osd_up"] < metrics["osd_in"]:
            issues.append("One or more OSDs are DOWN")

    if metrics["mon_quorum"] is not None and metrics["mon_quorum"] != 1:
        issues.append("Monitor quorum issue detected")

    if metrics["pg_degraded"] is not None and metrics["pg_degraded"] > 0:
        issues.append("Degraded placement groups detected")

    if not issues:
        return "No critical issues detected. Ceph cluster is operating normally."

    return " | ".join(issues)

# ---------------- FAILURE PREDICTION ----------------
def predict_failure(metrics):
    score = 0
    reasons = []

    if metrics["cluster_health"] != 1:
        score += 40
        reasons.append("Unhealthy cluster state")

    if metrics["osd_up"] < metrics["osd_in"]:
        score += 30
        reasons.append("OSD availability risk")

    if metrics["pg_degraded"] and metrics["pg_degraded"] > 0:
        score += 20
        reasons.append("Degraded PGs detected")

    if score < 30:
        level = "LOW"
    elif score < 60:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return level, score, reasons or ["No immediate failure indicators"]

# ---------------- PDF GENERATION ----------------
def generate_pdf(metrics, rca, prediction):
    level, score, reasons = prediction

    c = canvas.Canvas(PDF_FILE, pagesize=A4)
    width, height = A4

    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Ceph Storage – RCA & Failure Prediction Report")

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Cluster Metrics")

    c.setFont("Helvetica", 10)
    y -= 20
    for k, v in metrics.items():
        c.drawString(70, y, f"{k}: {v}")
        y -= 15

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Root Cause Analysis")

    c.setFont("Helvetica", 10)
    y -= 20
    c.drawString(70, y, rca)

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Failure Risk Prediction")

    c.setFont("Helvetica", 10)
    y -= 20
    c.drawString(70, y, f"Risk Level: {level}")
    y -= 15
    c.drawString(70, y, f"Risk Score: {score}")

    y -= 20
    c.drawString(70, y, "Reasons:")
    y -= 15
    for r in reasons:
        c.drawString(90, y, f"- {r}")
        y -= 15

    c.showPage()
    c.save()

# ---------------- MAIN ----------------
def main():
    print("\n[1] Collecting Ceph metrics from Prometheus...")
    metrics = collect_ceph_metrics()
    print(json.dumps(metrics, indent=2))

    print("\n[2] Performing RCA...")
    rca = generate_rca(metrics)
    print(rca)

    print("\n[3] Predicting failure risk...")
    prediction = predict_failure(metrics)

    print("\n[4] Generating PDF report...")
    generate_pdf(metrics, rca, prediction)

    print(f"\n✅ PDF Generated Successfully: {PDF_FILE}")

if __name__ == "__main__":
    main()
