#!/usr/bin/env python3
import requests
import json
from fpdf import FPDF
from datetime import datetime

# ==========================
# CONFIG
# ==========================
PROMETHEUS_URL = "http://localhost:9090"  # Prometheus running locally
CEPH_METRICS = [
    "ceph_health_status",
    "pg_degraded",
    "pg_undersized",
    "osd_down",
    "osd_up"
]

# ==========================
# FUNCTIONS
# ==========================

def query_prometheus(query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get("data", {}).get("result", [])
        if not result:
            return None
        # Prometheus returns value as [timestamp, value]
        return float(result[0]["value"][1]) if isinstance(result[0]["value"][1], (str, float)) else result[0]["value"][1]
    except Exception as e:
        print(f"Error querying Prometheus for {query}: {e}")
        return None

def collect_ceph_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    metrics = {}
    for metric in CEPH_METRICS:
        metrics[metric] = query_prometheus(metric)
    return metrics

def generate_rca(metrics):
    # Safe handling of None metrics
    pg_degraded = metrics.get("pg_degraded") or 0
    pg_undersized = metrics.get("pg_undersized") or 0
    osd_down = metrics.get("osd_down") or 0
    cluster_health = metrics.get("ceph_health_status") or "UNKNOWN"

    root_causes = []
    impact = []
    immediate_action = []
    preventive_action = []

    if cluster_health == 0:  # Assuming 0=HEALTH_OK, 1=HEALTH_WARN, 2=HEALTH_ERR
        root_causes.append("No anomalies detected in Ceph cluster")
        impact.append("No customer-visible impact detected")
        immediate_action.append("No immediate remediation required")
        preventive_action.append("Continue standard monitoring and audits")
        failure_risk = "LOW RISK"
    else:
        if pg_degraded > 0:
            root_causes.append(f"{pg_degraded} placement groups are degraded")
            impact.append("Potential data unavailability or performance impact")
            immediate_action.append("Investigate OSDs hosting degraded PGs")
            preventive_action.append("Ensure adequate OSD count and redundancy")
        if pg_undersized > 0:
            root_causes.append(f"{pg_undersized} placement groups are undersized")
            impact.append("Reduced data redundancy")
            immediate_action.append("Add or recover OSDs")
            preventive_action.append("Maintain pool size as per design")
        if osd_down > 0:
            root_causes.append(f"{osd_down} OSDs are down")
            impact.append("Data may be at risk if multiple OSDs fail")
            immediate_action.append("Bring down OSDs back online")
            preventive_action.append("Monitor OSD health and alerts")
        failure_risk = "HIGH RISK" if cluster_health > 0 else "LOW RISK"

    rca = {
        "root_cause": root_causes,
        "impact": impact,
        "immediate_action": immediate_action,
        "preventive_action": preventive_action,
        "failure_risk": failure_risk
    }

    return rca

def generate_pdf(rca, filename="Ceph_RCA_Report.pdf"):
    print("[2] Generating RCA PDF report...")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Ceph RCA & Failure Prediction Report", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(5)

    # Sections
    for section, items in rca.items():
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, section.replace("_", " ").title(), 0, 1)
        pdf.set_font("Arial", '', 12)
        if isinstance(items, list):
            for i, item in enumerate(items, 1):
                pdf.multi_cell(0, 7, f"{i}. {item}")
        else:
            pdf.multi_cell(0, 7, str(items))
        pdf.ln(3)

    pdf.output(filename)
    print(f"✅ PDF generated: {filename}")

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    metrics = collect_ceph_metrics()
    rca = generate_rca(metrics)
    generate_pdf(rca)

    # Print summary
    print("\n===== RCA SUMMARY =====")
    for k, v in rca.items():
        print(f"{k.replace('_', ' ').title()}: {v}")
