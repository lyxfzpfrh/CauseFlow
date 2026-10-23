import json, os, glob

# Build diagnosis based on manual analysis
diagnosis = {
    "entities": [
        {
            "name": "otel-demo/Deployment/ad",
            "contributing_factor": True,
            "reasoning": "Pods of ad service show high CPU throttling and request latency, causing request errors.",
            "evidence": "CPUThrottlingHigh alerts (6 firing) on pod ad-..., RequestLatency alert on ad, NoRequestsDetected alerts for ad, high RequestErrorRate for ad."
        },
        {
            "name": "otel-demo/Service/ad",
            "contributing_factor": False,
            "reasoning": "Service endpoint is impacted by its pods failing, leading to downstream errors.",
            "evidence": "NoRequestsDetected and RequestErrorRate alerts reference service ad."
        },
        {
            "name": "otel-demo/Deployment/frontend-proxy",
            "contributing_factor": False,
            "reasoning": "Frontend-proxy experiences request error spikes caused by downstream ad failures.",
            "evidence": "RequestErrorRate alerts for frontend-proxy fire concurrently with ad errors."
        },
        {
            "name": "otel-demo/Deployment/fraud-detection",
            "contributing_factor": False,
            "reasoning": "Fraud-detection shows request error alerts likely propagated from upstream failures.",
            "evidence": "RequestErrorRate alert for fraud-detection with warning severity."
        }
    ],
    "propagations": [
        {
            "source": "otel-demo/Deployment/ad",
            "target": "otel-demo/Deployment/frontend-proxy",
            "condition": "ad pods suffer CPU throttling and high latency, returning errors",
            "effect": "frontend-proxy receives error responses, raising RequestErrorRate alerts"
        },
        {
            "source": "otel-demo/Deployment/ad",
            "target": "otel-demo/Deployment/fraud-detection",
            "condition": "ad service failures cause downstream calls to fail",
            "effect": "fraud-detection sees increased error rate alerts"
        }
    ],
    "alerts_explained": [
        {"alert": "CPUThrottlingHigh", "explanation": "CPU throttling > ~28% observed on ad and frontend pods, indicating resource contention.", "explained": True},
        {"alert": "RequestLatency", "explanation": "ad service request latency exceeds 1500ms, causing slow responses.", "explained": True},
        {"alert": "NoRequestsDetected", "explanation": "ad and fraud-detection services report zero requests, likely due to upstream failures.", "explained": True},
        {"alert": "RequestErrorRate", "explanation": "High error rate warnings for ad, frontend-proxy, and fraud-detection services.", "explained": True},
        {"alert": "InfoInhibitor", "explanation": "Informational alert used to suppress noisy info alerts; not directly related to incident.", "explained": True}
    ]
}

output_path = os.path.join(os.getcwd(), "agent_output.json")
with open(output_path, "w") as f:
    json.dump(diagnosis, f, indent=2)
print(f"Wrote diagnosis to {output_path}")
