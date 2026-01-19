# 🚨 HPOneView-PagerDuty Bridge

**Enterprise-grade alert routing system for infrastructure monitoring**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-blue.svg)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-orange.svg)](https://argoproj.github.io/cd/)
[![Helm](https://img.shields.io/badge/Helm-3.0+-blue.svg)](https://helm.sh/)

> **A production-ready Kubernetes application that bridges HP OneView infrastructure monitoring with PagerDuty incident management, featuring GitOps deployment, comprehensive observability, and enterprise security**

## 🎯 Overview

HPOneView-PagerDuty Bridge is an intelligent alert routing system that monitors HP OneView infrastructure for critical hardware alerts and automatically routes them to PagerDuty for immediate on-call response.

### The Problem

Manual monitoring of HP OneView alerts resulted in:
- ⏰ **Delayed incident response** (30+ minutes average detection time)
- 👥 **24/7 manual console monitoring** required
- 📧 **Missed critical alerts** during off-hours
- 💰 **Increased MTTR** (Mean Time To Resolution)

### The Solution

An automated alert processing system that:
- ✅ Monitors OneView **24/7 automatically**
- ✅ Routes critical alerts **instantly** to PagerDuty (< 1 second)
- ✅ **Eliminates manual monitoring** overhead entirely
- ✅ Reduces incident response time by **97%**

## 🏗️ Architecture

### Component Design
```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌──────────────────┐                 │
│  │  HP OneView │         │  Kubernetes      │                 │
│  │  Appliance  │────────▶│  Cluster         │                 │
│  └─────────────┘  REST   └──────────────────┘                 │
│      (Polling           │                                      │
│       every 3m)         ▼                                      │
│                  ┌─────────────────────────┐                   │
│                  │   Web Pods (3-10)       │◀────────┐        │
│                  │   ├─ Flask API          │         │        │
│                  │   ├─ Health Endpoints   │      Contour     │
│                  │   ├─ Webhook Handler    │      HTTPProxy   │
│                  │   └─ Prometheus Metrics │      (Ingress)   │
│                  └──────────┬──────────────┘         │        │
│                             │                        │        │
│                             ▼                        │        │
│                  ┌─────────────────────────┐         │        │
│                  │   Poller Pod (1)        │         │        │
│                  │   ├─ Background Worker  │         │        │
│                  │   ├─ Alert Fetching     │         │        │
│                  │   ├─ Session Mgmt       │         │        │
│                  │   └─ Deduplication      │         │        │
│                  └──────────┬──────────────┘         │        │
│                             │                        │        │
│                  ┌──────────▼──────────────┐         │        │
│                  │   External Secrets      │         │        │
│                  │   ├─ Vault Integration  │         │        │
│                  │   └─ Secret Injection   │         │        │
│                  └──────────┬──────────────┘         │        │
│                             │                        │        │
│                             ▼                        │        │
│                  ┌─────────────────────────┐         │        │
│                  │   PagerDuty Events API  │         │        │
│                  │   └─ Alert Routing      │         │        │
│                  └──────────┬──────────────┘         │        │
│                             │                        │        │
│                             ▼                        │        │
│                  ┌─────────────────────────┐         │        │
│                  │   On-Call Engineers     │         │        │
│                  │   ├─ Mobile App         │         │        │
│                  │   ├─ SMS                │         │        │
│                  │   └─ Phone Call         │         │        │
│                  └─────────────────────────┘         │        │
│                                                      │        │
│  OBSERVABILITY STACK:                               │        │
│  ├─ Prometheus (Metrics Collection) ◀───────────────┘        │
│  ├─ ServiceMonitor (Auto-discovery)                          │
│  ├─ Request Tracing (Correlation IDs)                        │
│  └─ Structured Logging (JSON logs)                           │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Dual-Deployment Pattern

The application uses a **specialized dual-deployment architecture**:

#### 🌐 Web Deployment
- **Purpose**: Handle external API requests
- **Scaling**: Horizontal Pod Autoscaler (CPU/Memory based)
- **Resources**: 256Mi memory, 200m CPU (request)
- **Replicas**: 3-10 (auto-scaling)

#### 🔄 Poller Deployment
- **Purpose**: Background alert polling from OneView
- **Scaling**: Fixed single replica (singleton pattern)
- **Resources**: 512Mi memory, 300m CPU (request)
- **Replicas**: 1 (singleton)

**Why This Pattern?**
- Separation of concerns: Web traffic handling scales independently from polling
- Resource efficiency: Polling doesn't need multiple replicas
- Race condition prevention: Single poller prevents duplicate alert fetching
- High availability: Web pods handle failures; poller restarts on crash

## ✨ Features

### Alert Processing
- ✅ Thread-safe deduplication cache prevents duplicate alerts
- ✅ Automatic TTL management and cleanup (24-hour retention)
- ✅ Resource name and category extraction from alerts
- ✅ Severity-based filtering (Critical alerts only)

### Session Management
- ✅ Automatic session renewal 1 hour before expiry (22-hour lifetime)
- ✅ Connection pooling with retry logic (3 attempts, exponential backoff)
- ✅ Configurable SSL verification with CA certificate support
- ✅ Session validity monitoring via Prometheus metrics

### High Availability
- ✅ 3 web pod replicas with pod anti-affinity
- ✅ Pod Disruption Budget (minimum 2 pods available)
- ✅ Horizontal Pod Autoscaler (3-10 pods, CPU 70%, Memory 80%)
- ✅ Liveness and readiness probes for self-healing

### Security
- ✅ HashiCorp Vault integration via External Secrets Operator
- ✅ Kubernetes NetworkPolicy with zero-trust principles
- ✅ RBAC with minimal service account permissions
- ✅ Rate limiting (50 req/min with burst of 10)
- ✅ Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)

### Observability
- ✅ Prometheus metrics with ServiceMonitor
- ✅ Custom metrics for alerts processed, sent, and failed
- ✅ API latency and authentication duration tracking
- ✅ Request ID correlation for distributed tracing

## 📊 Prometheus Metrics

| Metric Name | Type | Description |
|------------|------|-------------|
| `oneview_alerts_processed_total` | Counter | Total OneView alerts processed |
| `pagerduty_alerts_sent_total` | Counter | Total alerts sent to PagerDuty |
| `pagerduty_alerts_failed_total` | Counter | Failed PagerDuty alerts (with reason label) |
| `oneview_auth_duration_seconds` | Histogram | OneView authentication duration |
| `oneview_api_latency_seconds` | Histogram | OneView API request latency |
| `oneview_session_active` | Gauge | OneView session status (1=active, 0=inactive) |
| `processed_alerts_count` | Gauge | Number of processed alerts in memory |
| `alert_delivery_duration_seconds` | Histogram | Time to deliver alert to PagerDuty |

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for Kubernetes liveness probe |
| `/ready` | GET | Readiness check for Kubernetes readiness probe |
| `/oneview-webhook` | POST | Receives webhook alerts from HPE OneView |
| `/test-connection` | GET | Tests connectivity with HPE OneView |
| `/force-poll` | POST | Manually triggers alert polling |
| `/metrics` | GET | Prometheus metrics endpoint |

## 🛠️ Technology Stack

### Application Layer
- **Language**: Python 3.11
- **Framework**: Flask 3.0 with Gunicorn 21.2 WSGI server
- **Key Libraries**: requests (with retry logic), prometheus-client, urllib3

### Infrastructure Layer
- **Container Platform**: Docker (multi-stage builds)
- **Orchestration**: Kubernetes 1.24+
- **Package Manager**: Helm 3
- **GitOps**: ArgoCD
- **Image Registry**: Docker Hub / Harbor / Any OCI registry

### Security & Observability
- **Secrets Management**: HashiCorp Vault with External Secrets Operator
- **Monitoring**: Prometheus with ServiceMonitor
- **Ingress**: Contour with HTTPProxy
- **Network Security**: Kubernetes NetworkPolicy

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (1.24+)
- Helm 3
- kubectl configured
- ArgoCD (optional, for GitOps)
- HP OneView appliance
- PagerDuty account with routing key

### Installation

#### Option 1: Quick Helm Install
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/hponeview-pagerduty-bridge.git
cd hponeview-pagerduty-bridge

# Create namespace
kubectl create namespace oneview-bridge

# Create secrets (for testing - use Vault in production!)
kubectl create secret generic oneview-pagerduty-secrets \
  --namespace oneview-bridge \
  --from-literal=ONEVIEW_HOST='oneview.example.com' \
  --from-literal=ONEVIEW_USERNAME='administrator' \
  --from-literal=ONEVIEW_PASSWORD='your-password' \
  --from-literal=PAGERDUTY_ROUTING_KEY='your-routing-key' \
  --from-literal=POLL_INTERVAL='180'

# Install with Helm
helm install hponeview-bridge ./helm \
  --namespace oneview-bridge \
  --set externalSecrets.enabled=false
```

#### Option 2: Production with ArgoCD
```bash
# Deploy ArgoCD Application
kubectl apply -f argocd/application.yaml

# Sync application
argocd app sync hponeview-pagerduty-bridge
```

### Verification
```bash
# Check pods
kubectl get pods -n oneview-bridge

# View logs
kubectl logs -n oneview-bridge -l component=poller --tail=50 --follow

# Test connectivity
kubectl exec -n oneview-bridge deploy/hponeview-pagerduty-bridge-web -- \
  curl -s http://localhost:5000/test-connection
```

## ⚙️ Configuration

### Environment Variables

Required secrets (managed via Vault or Kubernetes Secrets):

| Variable | Description |
|----------|-------------|
| `ONEVIEW_HOST` | HPE OneView hostname (without https://) |
| `ONEVIEW_USERNAME` | OneView API username |
| `ONEVIEW_PASSWORD` | OneView API password |
| `PAGERDUTY_ROUTING_KEY` | PagerDuty Events API v2 routing key |
| `POLL_INTERVAL` | Alert polling interval in seconds (default: 180) |

Optional configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `ONEVIEW_SSL_VERIFY` | Enable SSL verification | `false` |
| `ONEVIEW_CACERT` | Path to CA certificate bundle | - |
| `GUNICORN_MAIN_PROCESS` | Enable polling in this process | `false` |
| `GUNICORN_WORKERS` | Number of Gunicorn workers | `4` |
| `LOG_LEVEL` | Logging verbosity | `info` |

### Resource Limits

| Component | CPU Request | Memory Request | Memory Limit |
|-----------|-------------|----------------|--------------|
| Web Pods | 200m | 256Mi | 1Gi |
| Poller Pod | 300m | 512Mi | 2Gi |

### Auto-Scaling Policy
```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

## 📈 Monitoring

### Health Checks

**Web Pods**:
```bash
curl http://oneview-bridge.example.com/health

# Response includes poller status
{
  "status": "healthy",
  "oneview_configured": true,
  "pagerduty_configured": true,
  "poller_status": {
    "healthy": true,
    "oneview_session_valid": true
  }
}
```

**Poller Pod**:
```bash
kubectl exec -n oneview-bridge deploy/hponeview-pagerduty-bridge-poller -- \
  curl localhost:5000/health

{
  "status": "healthy",
  "oneview_session_valid": true,
  "processed_alerts_count": 5
}
```

### Prometheus Queries
```promql
# Alert processing rate
rate(oneview_alerts_processed_total[5m])

# PagerDuty delivery success rate
rate(pagerduty_alerts_sent_total[5m]) / rate(oneview_alerts_processed_total[5m])

# Failed alerts by reason
rate(pagerduty_alerts_failed_total[5m]) by (reason)

# 95th percentile alert delivery time
histogram_quantile(0.95, rate(alert_delivery_duration_seconds_bucket[5m]))

# OneView API latency by endpoint
histogram_quantile(0.95, rate(oneview_api_latency_seconds_bucket[5m])) by (endpoint)

# Session uptime
oneview_session_active
```

## 🐛 Troubleshooting

### Common Issues

**Problem**: Web pods cannot reach poller pod

**Solution**: Verify NetworkPolicy allows inter-pod communication:
```bash
kubectl describe networkpolicy -n oneview-bridge
```

---

**Problem**: OneView authentication failures

**Solution**: Check session validity and credentials:
```bash
kubectl exec -n oneview-bridge deploy/hponeview-pagerduty-bridge-poller -- \
  curl -X GET localhost:5000/test-connection
```

---

**Problem**: Alerts not reaching PagerDuty

**Solution**: Check Prometheus metrics:
```bash
kubectl exec -n oneview-bridge deploy/hponeview-pagerduty-bridge-web -- \
  curl localhost:5000/metrics | grep pagerduty_alerts_failed_total
```

### Debugging

Enable debug logging:
```bash
# Update values.yaml
config:
  logLevel: "debug"

# Apply changes
helm upgrade hponeview-bridge ./helm --values helm/values.yaml
```

View logs:
```bash
# Web pods
kubectl logs -n oneview-bridge -l component=web --tail=100 -f

# Poller pod
kubectl logs -n oneview-bridge -l component=poller --tail=100 -f
```

## 🔐 Security

### Secrets Management
- All sensitive credentials stored in HashiCorp Vault
- Secrets automatically refreshed every hour via External Secrets Operator
- No secrets in Git repositories or container images

### Network Security
- Zero-trust NetworkPolicy with explicit allow rules only
- TLS termination at ingress controller
- Pod-to-pod communication restricted by NetworkPolicy

### RBAC
Service account has minimal permissions:
```yaml
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
  - apiGroups: ["external-secrets.io"]
    resources: ["externalsecrets", "secretstores"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
```

## 💻 Development

### Local Development

1. Set up Python environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r src/requirements.txt
```

2. Configure environment variables:
```bash
export ONEVIEW_HOST="oneview.example.com"
export ONEVIEW_USERNAME="administrator"
export ONEVIEW_PASSWORD="password"
export PAGERDUTY_ROUTING_KEY="your-routing-key"
export POLL_INTERVAL="180"
export GUNICORN_MAIN_PROCESS="true"
```

3. Run the application:
```bash
cd src
python app.py
```

### Building Docker Image
```bash
docker build -f src/Dockerfile -t hponeview-bridge:latest .
```

### Running Tests
```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Author

Shlomi Lory | DevOps Engineer 

## 🙏 Acknowledgments

- HP OneView API Documentation
- PagerDuty Events API v2
- Kubernetes community
- ArgoCD project
- External Secrets Operator team

## 📞 Support

For issues or questions:
- Open an issue in the repository
- Check the [documentation](docs/)
- Review [troubleshooting guide](#-troubleshooting)

---

**Built with ❤️ for reliable infrastructure monitoring**

*Questions? Open an issue or reach out via GitHub!*