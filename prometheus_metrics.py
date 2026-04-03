from prometheus_client import Histogram, Counter, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Metrics definitions
APPROVAL_LATENCY = Histogram(
    "subscription_approval_latency_seconds",
    "Latency between subscription submit and approval",
    buckets=(1, 5, 10, 60, 300, 3600, 86400)
)

APPROVE_TOTAL = Counter(
    "subscription_approve_total",
    "Total approved subscriptions"
)

REJECT_TOTAL = Counter(
    "subscription_reject_total",
    "Total rejected subscriptions"
)

PENDING_GAUGE = Gauge(
    "subscription_pending_count",
    "Current pending subscriptions"
)

def start_metrics_server(port: int = 8000):
    """
    Start the Prometheus metrics server.
    """
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

# Helper functions for user code compatibility
def observe_approval_latency(latency: float):
    APPROVAL_LATENCY.observe(latency)

def inc_approve():
    APPROVE_TOTAL.inc()
    PENDING_GAUGE.dec()

def inc_reject():
    REJECT_TOTAL.inc()
    PENDING_GAUGE.dec()
