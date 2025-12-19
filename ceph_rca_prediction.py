#!/usr/bin/env python3
"""
Ceph RCA & Failure Prediction Script
Generates a PDF report with Root Cause Analysis, Impact, Immediate Action,
Preventive Action, and Failure Risk based on Ceph metrics collected from Prometheus.
"""

import requests
import json
from datetime import datetime
from fpdf import FPDF

# -----------------------------
# CONFIGURATION
# -----------------------------
PROMETHEUS_URL = "http://127.0.0.1:9090"  # Prometheus base URL
METRICS_QUERIES = {
    "osd_down": "ceph_osd_down",
    "pg_degraded": "ceph_pg_degraded",
    "pg_undersized": "ceph_pg_undersized",
    "cluster_health": "ceph_health_status"
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def query_prometheus(query):
    """Query Prometheus and return numeric value (0 if not available)."""
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        r.raise_for_status()
        result = r.json()["data"]["result"]
        if result:
            return float(result[0]["value"][1])
        else:
            return 0
    except Exception as e:
        print(f"[WARN] Failed to query Prometheus metric '{query}': {e}")
        return 0

def collect_ceph_metrics():
    """Collect Ceph metrics from Prometheus."""
    print("[1] Collecting Ceph metrics from Prometheus...")
    metrics = {}
    for key, query in METRICS_QUERIES.items():
        metrics[key] = query_prometheus(query)
    return metrics

def generate_rca(metrics):
    """Generate Root Cause Analysis based on metrics."""
    root_cause = []
    impact = []
    immediate = []
    preventive = []

    # Check OSD status
    osd_down = int(metrics.get("osd_down", 0))
    pg_degraded = int(metrics.get("pg_degraded", 0))
    pg_undersized = int(metrics.get("pg_undersized", 0))

    if osd_down > 0:
        root_cause.append(f"{osd_down} OSD(s) are down")
        impact.append("Data availability and redundancy might be affected")
        immediate.append("Investigate and restart the down OSD(s)")
        preventive.append("Set up monitoring and alerts for OSD failures")

    if pg_degraded > 0:
        root_cause.append(f"{pg_degraded} placement groups are degraded")
        impact.append("Potential data inconsistency")
        immediate.append("Trigger PG recovery")
        preventive.append("Monitor cluster health and PGs regularly")

    if pg_undersized > 0:
        root_cause.append(f"{pg_undersized} placement groups are undersized")
        impact.append("Reduced replication factor, data at risk")
        immediate.append("Ensure OSDs are up and PGs are properly sized")
        preventive.append("Maintain minimum required OSD count")

    if not root_cause:
        root_cause.append("No anomalies detected in Ceph cluster")
        impact.append("No customer-visible impact detected")
        immediate.append("No immediate remediation required")
        preventive.append("Continue standard monitoring and audits")

    # Determine failure risk
    if osd_down > 0 or pg_degraded > 0 or pg_undersized > 0:
        risk = "HIGH RISK"
    else:
        risk = "LOW RISK"

    rca_summary = {
        "Root Cause": root_cause,
        "Impact": impact,
        "Immediate Action": immediate,
        "Preventive Action": preventive,
        "Failure Risk": risk
    }
    return rca_summary

def generate_pdf_report(rca_summary, filename="Ceph_RCA_Report.pdf"):
    """Generate a PDF report for RCA."""
    print("[2] Generating RCA PDF report...")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ceph RCA & Failure Prediction Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(5)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)

    for section, items in rca_summary.items():
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, section, ln=True)
        pdf.set_font("Arial", "", 12)
        for item in items:
            pdf.multi_cell(0, 8, f"- {item}")
        pdf.ln(3)

    pdf.output(filename)
    print(f"✅ PDF generated: {filename}")

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    metrics = collect_ceph_metrics()
    rca_summary = generate_rca(metrics)
    generate_pdf_report(rca_summary)

    print("\n===== RCA SUMMARY =====")
    for key, value in rca_summary.items():
        print(f"{key}: {value}")
