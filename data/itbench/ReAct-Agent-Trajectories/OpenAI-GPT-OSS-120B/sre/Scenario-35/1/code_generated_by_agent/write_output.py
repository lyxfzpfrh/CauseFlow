"""Write the final diagnosis JSON to the required leaderboard path.

The script assembles a hard‑coded diagnosis based on the observed alerts in the
snapshot. It focuses on the otel-demo namespace as requested.
"""

import json, pathlib

diagnosis = {
    "entities": [
        {
            "name": "otel-demo/Deployment/frontend",
            "contributing_factor": True,
            "reasoning": "CPU throttling on the frontend container caused high latency and request failures.",
            "evidence": "Alert CPUThrottlingHigh (info) firing for pod frontend-675fd7b5c5-cmhqq and RequestErrorRate warnings for service frontend."
        },
        {
            "name": "otel-demo/Service/frontend",
            "contributing_factor": False,
            "reasoning": "Frontend service returned 5xx errors due to upstream CPU throttling.",
            "evidence": "RequestErrorRate alert firing for service frontend (warning)."
        },
        {
            "name": "otel-demo/Service/frontend-proxy",
            "contributing_factor": False,
            "reasoning": "Proxy observed errors propagated from the frontend service.",
            "evidence": "RequestErrorRate alert firing for service frontend-proxy (warning)."
        },
        {
            "name": "otel-demo/Service/ad",
            "contributing_factor": False,
            "reasoning": "No traffic observed because upstream services were failing.",
            "evidence": "NoRequestsDetected alert firing for service ad (warning)."
        }
    ],
    "propagations": [
        {
            "source": "otel-demo/Deployment/frontend",
            "target": "otel-demo/Service/frontend",
            "condition": "CPU throttling prevents request processing",
            "effect": "Service returned increased error rate"
        },
        {
            "source": "otel-demo/Service/frontend",
            "target": "otel-demo/Service/frontend-proxy",
            "condition": "Frontend errors cause upstream failures",
            "effect": "Proxy observed higher error rate"
        },
        {
            "source": "otel-demo/Service/frontend",
            "target": "otel-demo/Service/ad",
            "condition": "Downstream calls to ad stopped",
            "effect": "Ad service saw zero requests"
        }
    ],
    "alerts_explained": [
        {"alert": "CPUThrottlingHigh", "explanation": "High CPU throttling indicates the container is being limited by the kernel, leading to latency.", "explained": True},
        {"alert": "RequestErrorRate", "explanation": "Error rate >0 for the listed services shows they are returning errors.", "explained": True},
        {"alert": "NoRequestsDetected", "explanation": "Zero request count for service ad is a downstream symptom.", "explained": True},
        {"alert": "Watchdog", "explanation": "Always‑firing sanity check; not related to the incident.", "explained": True},
        {"alert": "InfoInhibitor", "explanation": "Inhibits info alerts; not directly relevant.", "explained": True},
        {"alert": "KubeSchedulerDown", "explanation": "Cluster component down; outside otel-demo namespace focus.", "explained": True},
        {"alert": "KubeControllerManagerDown", "explanation": "Cluster component down; outside otel-demo namespace focus.", "explained": True},
        {"alert": "KubeClientCertificateExpiration", "explanation": "Certificate expiry warning; not causing service errors.", "explained": True},
        {"alert": "PrometheusNotConnectedToAlertmanagers", "explanation": "Prometheus connectivity issue; not affecting otel-demo services.", "explained": True}
    ]
}

# Write to the leaderboard results directory as required
out_path = pathlib.Path("/root/projects/open_source/zero/leaderboard_results/react with code_openai_gpt-oss-120b_07ccdb1/Scenario-35/1/agent_output.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(diagnosis, indent=2))
print("Wrote diagnosis to", out_path)
