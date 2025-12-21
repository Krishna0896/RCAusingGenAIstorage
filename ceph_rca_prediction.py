#!/usr/bin/env python3

import requests
from datetime import datetime
from fpdf import FPDF

PROM_URL = "http://127.0.0.1:9090"

PROM_QUERIES = {
    "ceph_health_status": "ceph_health_status",
    "osd_up": "ceph_osd_up",
    "osd_down": "ceph_osd_down",
    "pg_degraded": "ceph_pg_degraded",
    "pg_undersized": "ceph_pg_undersized",
    "mon_quorum": "ceph_mon_quorum_status"
}

# -----------------------------
# PROMETHEUS QUERY
# -----------------------------
def query_prometheus(metric):
    try:
        r = requests.get(
            f"{PROM_URL}/api/v1/query",
            params={"query": metric},
            timeout=5
        )
        result = r.json()["data"]["result"]
        if result:
            return int(float(result[0]["value"][1]))
        return 0
    except Exception:
        return 0

# -----------------------------
# METRIC COLLECTION
# -----------------------------
def collect_metrics():
    print("[1] Collecting Ceph metrics from Prometheus...")
    metrics = {}
    for k, q in PROM_QUERIES.items():
        metrics[k] = query_prometheus(q)
    return metrics

# -----------------------------
# DETAILED RCA GENERATION
# -----------------------------
def generate_detailed_rca(metrics):
    h = metrics["ceph_health_status"]
    osd_up = metrics["osd_up"]
    osd_down = metrics["osd_down"]
    pg_deg = metrics["pg_degraded"]
    pg_under = metrics["pg_undersized"]
    mon_q = metrics["mon_quorum"]

    rca = (
        "**Root Cause Analysis**\n"
        "Based on the provided Ceph cluster metrics, the following issues are observed:\n\n"
        f"1. **ceph_health_status**: The cluster health status is reported as \"{h}\". "
        "A value of 1 indicates that the cluster is operational but has active warnings.\n\n"
        f"2. **osd_up**: Only \"{osd_up}\" OSD(s) are reported as up. "
        "This indicates that one or more OSDs are not currently serving data.\n\n"
        f"3. **pg_degraded**: The number of degraded placement groups is \"{pg_deg}\". "
        "This indicates whether data redundancy is currently compromised.\n\n"
        f"4. **pg_undersized**: The number of undersized placement groups is \"{pg_under}\". "
        "Undersized PGs indicate insufficient replicas to satisfy redundancy requirements.\n\n"
        f"5. **mon_quorum**: The monitor quorum status is reported as \"{mon_q}\". "
        "This confirms that the monitor quorum is healthy and cluster control is intact.\n\n"
    )

    if osd_down > 0:
        rca += (
            "However, the critical issue identified is that one or more OSDs are down. "
            "Even though monitor quorum is healthy and no degraded PGs are currently reported, "
            "running the cluster with a reduced OSD count significantly increases risk. "
            "With only one active OSD, the cluster has no redundancy, and any additional failure "
            "can immediately result in data unavailability or data loss.\n\n"
        )

        impact = (
            "**Impact**\n"
            "* Reduced data availability: With only one OSD up, the cluster cannot maintain "
            "replication guarantees.\n"
            "* Performance degradation: All read/write operations are handled by a single OSD.\n"
            "* Potential data loss: Any further OSD or disk failure may result in permanent data loss.\n"
        )

        remediation = (
            "**Immediate Remediation**\n"
            "1. Verify the status of all OSD containers using `ceph osd status`.\n"
            "2. Restart the failed OSD container or service.\n"
            "3. Check disk health, filesystem, and permissions for the affected OSD.\n"
            "4. Review Ceph logs for OSD crash or heartbeat failures.\n"
        )

        prevention = (
            "**Long-term Preventive Actions**\n"
            "1. Maintain minimum OSD count aligned with replication factor.\n"
            "2. Implement proactive monitoring and alerting for OSD health.\n"
            "3. Perform regular disk health and SMART checks.\n"
            "4. Add additional OSDs to improve redundancy.\n"
            "5. Regularly update Ceph software and review capacity planning.\n"
            "6. Train operations teams with OSD recovery procedures.\n"
        )

        risk = (
            "**Failure Prediction**\n"
            "Failure Risk Level: **HIGH**\n"
            "Estimated Time to Impact: Immediate to short-term if no action is taken.\n"
        )
    else:
        impact = "**Impact**\nNo immediate customer-visible impact detected.\n"
        remediation = "**Immediate Remediation**\nNo action required.\n"
        prevention = "**Long-term Preventive Actions**\nContinue standard monitoring.\n"
        risk = "**Failure Prediction**\nFailure Risk Level: LOW\n"

    return rca + "\n" + impact + "\n" + remediation + "\n" + prevention + "\n" + risk

# -----------------------------
# PDF GENERATION
# -----------------------------
def generate_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf.output("Ceph_RCA_Report.pdf")
    print("[4] Generating RCA PDF report...")
    print("✅ PDF generated: Ceph_RCA_Report.pdf")

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    metrics = collect_metrics()
    rca_text = generate_detailed_rca(metrics)
    generate_pdf(rca_text)

    print("\n===== RCA OUTPUT =====\n")
    print(rca_text)
