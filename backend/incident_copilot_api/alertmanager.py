from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .schemas import Alert, AlertmanagerAlert


@dataclass(frozen=True, slots=True)
class AlertProfile:
    incident_type: str
    expected_service: str
    title: str


ALERT_PROFILES = {
    "HighCheckoutErrorRate": AlertProfile(
        "checkout-degradation", "checkout-api", "Checkout service degradation"
    ),
    "SearchServiceSaturation": AlertProfile(
        "search-degradation", "search-api", "Search service degradation"
    ),
    "ReportingWorkerLowDisk": AlertProfile(
        "reporting-storage", "reporting-worker", "Reporting worker storage alert"
    ),
    "EmailDeliveryBacklog": AlertProfile(
        "email-backlog", "notification-service", "Email delivery backlog"
    ),
    "HighAuthenticationFailureRate": AlertProfile(
        "auth-degradation", "auth-service", "Authentication service degradation"
    ),
}


def profile_for(alert: AlertmanagerAlert) -> AlertProfile | None:
    alert_name = alert.labels.get("alertname", "")
    profile = ALERT_PROFILES.get(alert_name)
    if profile is None or alert.labels.get("service") != profile.expected_service:
        return None
    return profile


def internal_alert(alert: AlertmanagerAlert) -> Alert:
    labels = alert.labels
    annotations = alert.annotations
    return Alert(
        alert_type=labels["alertname"],
        service=labels["service"],
        environment=labels.get("environment", "unknown"),
        region=labels.get("region", "global"),
        severity=labels.get("severity", "warning"),
        summary=annotations.get("summary") or labels["alertname"],
        started_at=alert.starts_at,
    )


def monitoring_event_reference(alert: AlertmanagerAlert) -> str:
    """Identify one alert episode while allowing the same fingerprint to recur later."""

    value = f"{alert.fingerprint}|{alert.starts_at}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
