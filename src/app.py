from flask import Flask, request, jsonify, g
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import logging
import threading
import time
from datetime import datetime, timedelta
import signal
import sys
import uuid
import urllib3
from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Suppress SSL warnings if verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging with request ID support
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            from flask import has_request_context
            if has_request_context():
                record.request_id = getattr(g, 'request_id', 'N/A')
            else:
                record.request_id = 'startup'
        except:
            record.request_id = 'N/A'
        return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(request_id)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

# Global variables
oneview_client = None
processed_alerts = {}  # Dict: alert_id -> timestamp for TTL
processed_alerts_lock = threading.Lock()  # Thread-safe access
polling_thread = None
shutdown_event = threading.Event()

# Prometheus metrics
ALERTS_PROCESSED = Counter('oneview_alerts_processed_total', 'Total OneView alerts processed')
ALERTS_SENT_TO_PAGERDUTY = Counter('pagerduty_alerts_sent_total', 'Total alerts sent to PagerDuty')
ALERTS_FAILED = Counter('pagerduty_alerts_failed_total', 'Failed PagerDuty alerts', ['reason'])
ONEVIEW_AUTH_DURATION = Histogram('oneview_auth_duration_seconds', 'OneView authentication duration')
ONEVIEW_API_LATENCY = Histogram('oneview_api_latency_seconds', 'OneView API request latency', ['endpoint'])
ACTIVE_ONEVIEW_SESSION = Gauge('oneview_session_active', 'OneView session status (1=active, 0=inactive)')
PROCESSED_ALERTS_COUNT = Gauge('processed_alerts_count', 'Number of processed alerts in memory')
ALERT_DELIVERY_DURATION = Histogram('alert_delivery_duration_seconds', 'Time to deliver alert to PagerDuty')


class OneViewClient:
    def __init__(self, host, username, password):
        # Remove https:// if present in host
        if host:
            host = host.replace('https://', '').replace('http://', '')
        self.host = f"https://{host}" if host else None
        self.username = username
        self.password = password
        self.session_id = None
        self.session_expires = None
        self.session = self._create_session_with_retries()
        
    def _create_session_with_retries(self):
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Add retry logic
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
        
    def authenticate(self):
        """Authenticate with OneView and get session ID"""
        if not all([self.host, self.username, self.password]):
            logger.error("OneView credentials not properly configured")
            return False
            
        try:
            auth_payload = {
                "userName": self.username,
                "password": self.password
            }
            
            # Enable SSL verification (configurable)
            verify_ssl = os.getenv('ONEVIEW_SSL_VERIFY', 'false').lower() == 'true'
            ca_cert = os.getenv('ONEVIEW_CACERT')
            
            start_time = time.time()
            
            response = self.session.post(
                f"{self.host}/rest/login-sessions",
                json=auth_payload,
                headers={"Content-Type": "application/json"},
                verify=ca_cert if ca_cert else verify_ssl,
                timeout=30
            )
            
            # Record authentication duration
            ONEVIEW_AUTH_DURATION.observe(time.time() - start_time)
            
            if response.status_code == 200:
                self.session_id = response.json().get('sessionID')
                # Refresh 1 hour before expiry (22 hours instead of 23)
                self.session_expires = datetime.now() + timedelta(hours=22)
                logger.info("Successfully authenticated with OneView")
                ACTIVE_ONEVIEW_SESSION.set(1)
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                ACTIVE_ONEVIEW_SESSION.set(0)
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            ACTIVE_ONEVIEW_SESSION.set(0)
            return False
    
    def is_session_valid(self):
        """Check if current session is still valid"""
        return (self.session_id is not None and 
                self.session_expires is not None and 
                datetime.now() < self.session_expires)
    
    def get_critical_alerts(self):
        """Fetch critical alerts from OneView"""
        try:
            if not self.is_session_valid():
                if not self.authenticate():
                    return []
            
            headers = {
                "Auth": self.session_id,
                "Content-Type": "application/json",
                "X-API-Version": "4600"
            }
            
            params = {
                "filter": "severity='Critical'",
                "sort": "created:desc"
            }
            
            # Enable SSL verification
            verify_ssl = os.getenv('ONEVIEW_SSL_VERIFY', 'false').lower() == 'true'
            ca_cert = os.getenv('ONEVIEW_CACERT')
            
            start_time = time.time()
            
            response = self.session.get(
                f"{self.host}/rest/alerts",
                headers=headers,
                params=params,
                verify=ca_cert if ca_cert else verify_ssl,
                timeout=30
            )
            
            # Record API latency
            ONEVIEW_API_LATENCY.labels(endpoint='get_alerts').observe(time.time() - start_time)
            
            if response.status_code == 200:
                alerts_data = response.json()
                raw_alerts = alerts_data.get('members', [])
                
                # Process alerts to extract resource names
                processed_alerts_list = []
                for alert in raw_alerts:
                    # Extract resource name from associatedResource
                    resource_name = 'Unknown Resource'
                    resource_category = 'OneView'
                    
                    # Get from associatedResource (most reliable)
                    associated_resource = alert.get('associatedResource', {})
                    if associated_resource and isinstance(associated_resource, dict):
                        resource_name = associated_resource.get('resourceName', 'Unknown Resource')
                        resource_category = associated_resource.get('resourceCategory', 'OneView')
                    
                    # Fallback to direct resourceName field
                    if resource_name == 'Unknown Resource':
                        resource_name = alert.get('resourceName', 'Unknown Resource')
                    
                    # Fallback to physicalResourceType
                    if resource_name == 'Unknown Resource':
                        resource_name = alert.get('physicalResourceType', 'Unknown Resource')
                    
                    # Create processed alert with extracted fields
                    processed_alert = alert.copy()  # Keep all original fields
                    processed_alert['resource'] = resource_name
                    processed_alert['resourceCategory'] = resource_category
                    
                    processed_alerts_list.append(processed_alert)
                
                logger.info(f"Retrieved {len(processed_alerts_list)} critical alerts from OneView")
                return processed_alerts_list
            else:
                logger.error(f"Failed to fetch alerts: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching alerts: {str(e)}")
            return []


def send_to_pagerduty(alert_data, pagerduty_routing_key):
    """Send alert to PagerDuty"""
    if not pagerduty_routing_key:
        logger.error("PagerDuty routing key not configured")
        ALERTS_FAILED.labels(reason='no_routing_key').inc()
        return False
        
    try:
        start_time = time.time()
        
        description = alert_data.get('description', 'No description')
        severity = alert_data.get('severity', 'critical')
        source = alert_data.get('resourceUri', 'OneView')
        alert_id = alert_data.get('uri', alert_data.get('resourceId', 'Unknown'))
        alert_state = alert_data.get('alertState', 'Active')
        resource_name = alert_data.get('resource', 'Unknown Resource')  # ← FIXED: Changed from 'resourceName'
        resource_category = alert_data.get('resourceCategory', 'OneView')
        
        if alert_state.lower() != 'active':
            return True
        
        event_action = "trigger"
        if alert_state.lower() in ['cleared', 'acknowledged']:
            event_action = "resolve"
        
        pd_payload = {
            "routing_key": pagerduty_routing_key,
            "event_action": event_action,
            "payload": {
                "summary": f"OneView Alert: {description} - Resource: {resource_name}",
                "severity": severity.lower(),
                "source": source,
                "timestamp": alert_data.get('created', datetime.now().isoformat()),
                "component": resource_name,
                "group": resource_category,
                "class": alert_data.get('alertTypeID', 'Alert'),
                "custom_details": {
                    "oneview_alert_id": alert_id,
                    "resource_name": resource_name,
                    "resource_category": resource_category,
                    "alert_type": alert_data.get('alertTypeID'),
                    "description": description,
                    "created": alert_data.get('created'),
                    "modified": alert_data.get('modified'),
                    "severity": severity,
                    "health_category": alert_data.get('healthCategory'),
                    "urgency": alert_data.get('urgency')
                }
            },
            "dedup_key": alert_id
        }
        
        response = requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=pd_payload,
            timeout=30
        )
        
        # Record delivery duration
        ALERT_DELIVERY_DURATION.observe(time.time() - start_time)
        
        if response.status_code == 202:
            ALERTS_SENT_TO_PAGERDUTY.inc()
            logger.info(f"Successfully sent alert to PagerDuty: {alert_id} - Resource: {resource_name}")
            return True
        else:
            ALERTS_FAILED.labels(reason='pagerduty_api_error').inc()
            logger.error(f"PagerDuty API error for resource {resource_name}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        ALERTS_FAILED.labels(reason='exception').inc()
        logger.error(f"Error sending to PagerDuty: {str(e)}")
        return False


def poll_oneview_alerts(app_config):
    """Background task to poll OneView for critical alerts"""
    logger.info("Starting OneView alert polling service")
    
    while not shutdown_event.is_set():
        try:
            if not oneview_client:
                logger.error("OneView client not configured")
                shutdown_event.wait(app_config.get('POLL_INTERVAL', 180))
                continue
            
            alerts = oneview_client.get_critical_alerts()
            
            new_alerts = 0
            for alert in alerts:
                if shutdown_event.is_set():
                    break
                    
                alert_id = alert.get('uri', alert.get('resourceId', 'Unknown'))
                current_time = datetime.now()
                
                # Thread-safe alert tracking
                with processed_alerts_lock:
                    if alert_id in processed_alerts:
                        continue
                    processed_alerts[alert_id] = current_time
                
                if send_to_pagerduty(alert, app_config.get('PAGERDUTY_ROUTING_KEY')):
                    ALERTS_PROCESSED.inc()
                    new_alerts += 1
            
            if new_alerts > 0:
                logger.info(f"Processed {new_alerts} new critical alerts")
            
            # TTL-based cleanup (keep for 24 hours)
            with processed_alerts_lock:
                cutoff = datetime.now() - timedelta(hours=24)
                alerts_to_remove = [
                    k for k, v in processed_alerts.items() if v < cutoff
                ]
                for alert_id in alerts_to_remove:
                    del processed_alerts[alert_id]
                
                if alerts_to_remove:
                    logger.info(f"Cleaned up {len(alerts_to_remove)} old alert records")
            
        except Exception as e:
            logger.error(f"Error in polling loop: {str(e)}")
        
        # Wait for next poll interval or shutdown
        shutdown_event.wait(app_config.get('POLL_INTERVAL', 180))


def create_app():
    """Application factory pattern for Gunicorn"""
    global oneview_client, polling_thread
    
    app = Flask(__name__)
    
    # Add ProxyFix middleware for Contour/Envoy
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,      # Trust X-Forwarded-For
        x_proto=1,    # Trust X-Forwarded-Proto
        x_host=1,     # Trust X-Forwarded-Host
        x_prefix=1    # Trust X-Forwarded-Prefix
    )
    
    # Load configuration from environment variables
    # (External Secrets injects these from Vault)
    config = {
        'PAGERDUTY_ROUTING_KEY': os.getenv('PAGERDUTY_ROUTING_KEY'),
        'ONEVIEW_HOST': os.getenv('ONEVIEW_HOST'),
        'ONEVIEW_USERNAME': os.getenv('ONEVIEW_USERNAME'),
        'ONEVIEW_PASSWORD': os.getenv('ONEVIEW_PASSWORD'),
        'POLL_INTERVAL': int(os.getenv('POLL_INTERVAL', '180')),
    }
    
    # Store config in app
    for key, value in config.items():
        if value:
            app.config[key] = value
    
    # Initialize OneView client
    if all(config.get(key) for key in ['ONEVIEW_HOST', 'ONEVIEW_USERNAME', 'ONEVIEW_PASSWORD']):
        oneview_client = OneViewClient(
            config['ONEVIEW_HOST'],
            config['ONEVIEW_USERNAME'],
            config['ONEVIEW_PASSWORD']
        )
        logger.info("OneView client initialized")
    else:
        logger.warning("OneView client not configured - missing required credentials")
    
    # Start polling thread only in designated poller pod
    # GUNICORN_MAIN_PROCESS is set to "true" only in poller deployment
    if (oneview_client and 
        config.get('PAGERDUTY_ROUTING_KEY') and 
        os.getenv('GUNICORN_MAIN_PROCESS', 'false').lower() == 'true'):
        polling_thread = threading.Thread(target=poll_oneview_alerts, args=(config,), daemon=True)
        polling_thread.start()
        logger.info("Started background polling thread")
    else:
        logger.info("Polling thread NOT started (web worker mode)")
    
    # Request ID tracking middleware
    @app.before_request
    def track_request():
        """Track request ID for distributed tracing"""
        g.request_id = request.headers.get('X-Request-Id') or str(uuid.uuid4())
        g.start_time = time.time()
    
    @app.after_request
    def log_request(response):
        """Log request completion"""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            logger.info(f"{request.method} {request.path} {response.status_code} {duration:.3f}s")
        return response
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for load balancers"""
        status = {
            "status": "healthy",
            "oneview_configured": oneview_client is not None,
            "pagerduty_configured": app.config.get('PAGERDUTY_ROUTING_KEY') is not None,
            "poll_interval": app.config.get('POLL_INTERVAL', 180),
            "polling_enabled": os.getenv('GUNICORN_MAIN_PROCESS', 'false').lower() == 'true',
            "processed_alerts_count": len(processed_alerts),
            "timestamp": datetime.now().isoformat(),
            "ingress_controller": "contour",
            "request_id": getattr(g, 'request_id', 'N/A')
        }
        
        # If this is a poller pod, add its own OneView session status
        if status["polling_enabled"]:
            if oneview_client:
                status["oneview_session_valid"] = oneview_client.is_session_valid()
        else:
            # This is a web pod - get status from poller pod
            try:
                # Construct poller service URL
                # Format: <service-name>.<namespace>.svc.cluster.local
                namespace = os.getenv('POD_NAMESPACE', 'oneviewbridge')
                poller_service = f"oneview-pagerduty-bridge-ovbridge-poller.{namespace}.svc.cluster.local"
                poller_url = f"http://{poller_service}/health"
                
                # Query poller health with short timeout
                poller_response = requests.get(poller_url, timeout=2)
                
                if poller_response.status_code == 200:
                    poller_data = poller_response.json()
                    status["poller_status"] = {
                        "healthy": True,
                        "oneview_session_valid": poller_data.get("oneview_session_valid", False),
                        "processed_alerts_count": poller_data.get("processed_alerts_count", 0),
                        "last_check_timestamp": poller_data.get("timestamp"),
                        "polling_enabled": poller_data.get("polling_enabled", False)
                    }
                    # Also set top-level oneview_session_valid for backward compatibility
                    status["oneview_session_valid"] = poller_data.get("oneview_session_valid", False)
                else:
                    status["poller_status"] = {
                        "healthy": False,
                        "error": f"Poller returned HTTP {poller_response.status_code}"
                    }
                    status["oneview_session_valid"] = False
            except requests.exceptions.Timeout:
                status["poller_status"] = {
                    "healthy": False,
                    "error": "Timeout connecting to poller pod"
                }
                status["oneview_session_valid"] = False
            except requests.exceptions.ConnectionError as e:
                status["poller_status"] = {
                    "healthy": False,
                    "error": f"Connection error: {str(e)}"
                }
                status["oneview_session_valid"] = False
            except Exception as e:
                status["poller_status"] = {
                    "healthy": False,
                    "error": f"Unexpected error: {str(e)}"
                }
                status["oneview_session_valid"] = False
        
        return jsonify(status), 200

    @app.route('/ready', methods=['GET'])
    def readiness_check():
        """Readiness check for Kubernetes"""
        if not oneview_client or not app.config.get('PAGERDUTY_ROUTING_KEY'):
            return jsonify({"status": "not ready", "reason": "missing configuration"}), 503
        
        return jsonify({"status": "ready"}), 200

    @app.route('/oneview-webhook', methods=['POST'])
    def oneview_webhook():
        """Process incoming OneView webhook alerts"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No JSON data received"}), 400
            
            # Check if already processed
            alert_id = data.get('uri', data.get('resourceId', 'Unknown'))
            
            with processed_alerts_lock:
                if alert_id in processed_alerts:
                    logger.info(f"Alert {alert_id} already processed, skipping")
                    return jsonify({"status": "already_processed", "alert_id": alert_id}), 200
            
            success = send_to_pagerduty(data, app.config.get('PAGERDUTY_ROUTING_KEY'))
            
            if success:
                with processed_alerts_lock:
                    processed_alerts[alert_id] = datetime.now()
                ALERTS_PROCESSED.inc()
                return jsonify({"status": "success", "message": "Alert sent to PagerDuty"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send to PagerDuty"}), 500
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route('/test-connection', methods=['GET'])
    def test_connection():
        """Test OneView connectivity"""
        if not oneview_client:
            return jsonify({"error": "OneView client not configured"}), 400
        
        try:
            if oneview_client.authenticate():
                alerts = oneview_client.get_critical_alerts()
                return jsonify({
                    "status": "success",
                    "message": "Successfully connected to OneView",
                    "critical_alerts_count": len(alerts)
                }), 200
            else:
                return jsonify({"error": "Failed to authenticate with OneView"}), 500
                
        except Exception as e:
            return jsonify({"error": f"Connection test failed: {str(e)}"}), 500

    @app.route('/force-poll', methods=['POST'])
    def force_poll():
        """Manual trigger for polling"""
        try:
            if not oneview_client:
                return jsonify({"error": "OneView client not configured"}), 400
            
            alerts = oneview_client.get_critical_alerts()
            processed = 0
            
            for alert in alerts:
                alert_id = alert.get('uri', alert.get('resourceId', 'Unknown'))
                
                with processed_alerts_lock:
                    if alert_id in processed_alerts:
                        continue
                
                if send_to_pagerduty(alert, app.config.get('PAGERDUTY_ROUTING_KEY')):
                    with processed_alerts_lock:
                        processed_alerts[alert_id] = datetime.now()
                    ALERTS_PROCESSED.inc()
                    processed += 1
            
            return jsonify({
                "status": "success",
                "alerts_found": len(alerts),
                "alerts_processed": processed
            }), 200
            
        except Exception as e:
            return jsonify({"error": f"Force poll failed: {str(e)}"}), 500

    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Prometheus metrics endpoint"""
        # Update gauge metrics with current values
        with processed_alerts_lock:
            PROCESSED_ALERTS_COUNT.set(len(processed_alerts))
        
        if oneview_client:
            ACTIVE_ONEVIEW_SESSION.set(1 if oneview_client.is_session_valid() else 0)
        else:
            ACTIVE_ONEVIEW_SESSION.set(0)
        
        # Return Prometheus format
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    return app


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create the app instance
app = create_app()

if __name__ == '__main__':
    # This block only runs when using python app.py directly
    # Not when using Gunicorn
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)