#!/usr/bin/env python3
import requests
import json
from fpdf import FPDF
from datetime import datetime

# === CONFIGURATION ===
PROMETHEUS_URL = "http://127.0.0.1:9090/api/v1/query"

# === FUNCTIONS ===

def query_prometheus(query):
    try:
        r = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]["result"]
        if not data:
            return None
        return float(data[0]["value"][1])
    except Exception as e:
        print(f"Failed to query Prometheus: {e}")
        return None

def collect_ceph_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")

    metrics = {
        "cluster_health": query_prometheus("ceph_health_status"),      # 0=OK,1=WARN,2=ERR
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "pg_degraded": query_prometheus("ceph_pg_degraded"),
        "pg_undersized": query_prometheus("ceph_pg_undersized"),
        "pg_unassigned": query_prometheus("ceph_pg_unassigned")
    }
    return metrics

def generate_rca(metrics):
    # Default safe values
    root_cause = ["No anomalies detected in Ceph cluster"]
    impact = ["No customer-visible impact detected"]
    immediate_action = ["No immediate remediation required"]
    preventive_action = ["Continue standard monitoring and audits"]
    failure_risk = "LOW RISK"

    # Analyze metrics
    if metrics["cluster_health"] == 1:  # HEALTH_WARN
        root_cause = []
        impact = []
        immediate_action = []
        preventive_action = []
        failure_risk = "MEDIUM RISK"

        if metrics["osd_up"] < metrics["osd_in"]:
            root_cause.append(f"{int(metrics['osd_in'] - metrics['osd_up'])} OSD(s) down")
            impact.append("Data redundancy reduced, potential performance degradation")
            immediate_action.append("Bring OSDs back online or mark as out")
            preventive_action.append("Ensure monitoring alerts for OSD failures")

        if metrics["pg_degraded"] > 0:
            root_cause.append(f"{int(metrics['pg_degraded'])} PG(s) degraded")
            impact.append("Data placement not fully redundant")
            immediate_action.append("Monitor PG recovery and reweight OSDs if needed")
            preventive_action.append("Maintain sufficient OSDs for pool replication")

        if metrics["pg_undersized"] > 0:
            root_cause.append(f"{int(metrics['pg_undersized'])} undersized PG(s)")
            impact.append("Some PGs have fewer copies than required")
            immediate_action.append("Investigate OSD failures or capacity issues")
            preventive_action.append("Plan capacity and replication properly")

        if metrics["pg_unassigned"] > 0:
            root_cause.append(f"{int(metrics['pg_unassigned'])} unassigned PG(s)")
            impact.append("Data may be temporarily unavailable")
            immediate_action.append("Check cluster logs and assign PGs")
            preventive_action.append("Ensure OSD availability and monitoring")

    return {
        "Root Cause": root_cause,
        "Impact": impact,
        "Immediate Action": immediate_action,
        "Preventive Action": preventive_action,
        "Failure Risk": failure_risk
    }

def generate_pdf_report(rca, filename="Ceph_RCA_Report.pdf"):
    print("[4] Generating RCA PDF report...")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Ceph Cluster RCA Report", 0, 1, "C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "C")
    pdf.ln(5)

    for section, items in rca.items():
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, section, 0, 1)
        pdf.set_font("Arial", "", 12)
        if isinstance(items, list):
            for item in items:
                pdf.multi_cell(0, 6, f"- {item}")
        else:
            pdf.multi_cell(0, 6, str(items))
        pdf.ln(3)

    pdf.output(filename)
    print(f"✅ PDF generated: {filename}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    metrics = collect_ceph_metrics()
    rca = generate_rca(metrics)
    
    print("\n===== RCA SUMMARY =====")
    for key, value in rca.items():
        print(f"{key}: {value}")

    generate_pdf_report(rca)
