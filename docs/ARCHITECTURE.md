# Architecture Guide

## System Overview

The HPOneView-PagerDuty Bridge is a production-grade microservice that provides intelligent alert routing between HP OneView infrastructure monitoring and PagerDuty incident management.

## Components

### 1. Web Deployment
- **Purpose**: HTTP API for webhooks and manual operations
- **Scaling**: 3-10 pods (HPA based on CPU/Memory)
- **Endpoints**: /health, /ready, /metrics, /oneview-webhook, /force-poll

### 2. Poller Deployment  
- **Purpose**: Background worker for periodic alert polling
- **Scaling**: 1 pod (singleton pattern)
- **Behavior**: Polls OneView every 180s for critical alerts

### 3. External Secrets
- **Purpose**: Secure secret injection from HashiCorp Vault
- **Refresh**: Hourly automatic refresh
- **Secrets**: API keys, credentials

### 4. Network Policy
- **Ingress**: Allow from ingress controller and Prometheus
- **Egress**: Allow to DNS, Vault, and HTTPS endpoints

### 5. Monitoring
- **Prometheus**: 7 custom metrics
- **ServiceMonitor**: Auto-discovery
- **Grafana**: Pre-built dashboards

## Data Flow

```
OneView Alert → Poller Pod → Deduplication → PagerDuty API → On-Call Engineer
```

## High Availability

- 3+ web pods with anti-affinity
- Pod Disruption Budget (min 2 available)
- Health/readiness probes
- Graceful shutdown (30s)
- Session management with auto-refresh

## Security

- Non-root containers
- Read-only root filesystem
- Network policies (zero-trust)
- RBAC (least privilege)
- Secrets in Vault (never in Git)
- Security headers (XSS, MIME-sniffing, clickjacking)
