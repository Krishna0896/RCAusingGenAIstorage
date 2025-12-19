import requests
import json
import sys
from datetime import datetime

# ---------------- CONFIG ----------------
PROMETHEUS_URL = "http://localhost:9090"
TIMEOUT = 10

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
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),

        # Ceph standard metrics
        "cluster_health": query_prometheus("ceph_health_status"),
        "osd_up": query_prometheus("ceph_osd_up"),
        "osd_in": query_prometheus("ceph_osd_in"),
        "mon_quorum": query_prometheus("ceph_mon_quorum_status"),
        "pg_degraded": query_prometheus("ceph_pg_degraded")
    }
    return metrics


# ---------------- RCA LOGIC ----------------
def generate_rca(metrics):
    issues = []

    if metrics["cluster_health"] is not None and metrics["cluster_health"] != 1:
        issues.append("Cluster health is WARNING or ERROR")

    if (
        metrics["osd_up"] is not None and
        metrics["osd_in"] is not None and
        metrics["osd_up"] < metrics["osd_in"]
    ):
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
        reasons.append("Degraded PGs increase data risk")

    if score < 30:
        level = "LOW"
    elif score < 60:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "risk_level": level,
        "risk_score": score,
        "reasons": reasons or ["No immediate failure indicators"]
    }


# ---------------- MAIN ----------------
def main():
    print("\n[1] Collecting Ceph metrics from Prometheus...")
    metrics = collect_ceph_metrics()
    print(json.dumps(metrics, indent=2))

    print("\n[2] Root Cause Analysis...")
    rca = generate_rca(metrics)
    print(rca)

    print("\n[3] Failure Risk Prediction...")
    prediction = predict_failure(metrics)

    print("\n--- Failure Prediction ---")
    print(f"Risk Level : {prediction['risk_level']}")
    print(f"Risk Score : {prediction['risk_score']}")
    print("Reasons:")
    for r in prediction["reasons"]:
        print(f" - {r}")


if __name__ == "__main__":
    main()
