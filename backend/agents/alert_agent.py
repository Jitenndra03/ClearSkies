"""
alert_agent.py
---------------
System Feature 9: Real-time Alerts

Decides WHETHER a dispatch is warranted and THROUGH WHICH channel, given
either (a) a fresh forecast/advisory risk-band crossing or (b) an
Emergency Detection Agent trigger -- then formats the dispatch record
that the Notification Service (mock push/SMS/IVR gateway per Section 8's
architecture) would actually send.

This agent deliberately does NOT call a real SMS/push gateway -- Section
16/7 of the plan scopes that to a "free/mock gateway" for the hackathon.
What it produces (recipient, channel, message, risk_level, status,
dispatched_at) is exactly the row shape `db.repository.insert_alert_log`
/ `fetch_recent_alerts` and `mock_data.generate_alert_feed` already use,
so swapping in a real Twilio/FCM call later only touches `_send()` below.

Role: Turns a risk-band advisory or an emergency alert into a channel-
      appropriate dispatch, and produces the log row for the Alerts page.
Inputs: ward, risk_level (from Advisory/Prediction agents) OR an
        EmergencyAlert (from Emergency Detection Agent), recipient
        channel preference.
Outputs: AlertDispatch (one per recipient/channel).
Talks to: Citizen Advisory Agent, Emergency Detection Agent (both feed
          this agent), Notification Service, Alerts UI page.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Risk bands that warrant proactively pushing a notification at all --
# "good"/"satisfactory" don't need to interrupt anyone.
NOTIFY_BANDS = {"moderate", "poor", "very_poor", "severe", "critical"}

# Escalation: higher-risk bands prefer more attention-grabbing channels.
# A citizen's own channel preference is still respected when given --
# this is only the fallback/auto-escalation choice.
DEFAULT_CHANNEL_BY_BAND = {
    "moderate": "app_feed",
    "poor": "push",
    "very_poor": "push",
    "severe": "sms",
    "critical": "sms",  # emergency-triggered alerts use this band
}


@dataclass
class AlertDispatch:
    recipient: str            # ward name or user_id
    channel: str               # push / sms / app_feed / ivr
    message: str
    risk_level: str
    status: str = "sent"       # sent / failed / suppressed
    dispatched_at: datetime = None

    def __post_init__(self):
        if self.dispatched_at is None:
            self.dispatched_at = datetime.now()


class RealTimeAlertAgent:
    """
    Role: Decides whether an advisory/emergency event should be dispatched,
          picks a channel, formats the message, and returns the log row.
    Inputs: ward, risk_level, optional preferred_channel, optional
            emergency context (for emergency-triggered dispatches).
    Outputs: AlertDispatch, or None if the risk band doesn't warrant a push.
    Talks to: Advisory Agent, Emergency Detection Agent, Notification
              Service (mock gateway), Alerts UI.
    """

    def should_notify(self, risk_level: str) -> bool:
        return risk_level in NOTIFY_BANDS

    def dispatch_advisory(
        self,
        ward: str,
        risk_level: str,
        advisory_message: str,
        preferred_channel: Optional[str] = None,
    ) -> Optional[AlertDispatch]:
        """Dispatch triggered by a routine forecast/advisory risk-band crossing."""
        if not self.should_notify(risk_level):
            return None

        channel = preferred_channel or DEFAULT_CHANNEL_BY_BAND.get(risk_level, "app_feed")
        return self._send(recipient=ward, channel=channel, message=advisory_message, risk_level=risk_level)

    def dispatch_emergency(
        self,
        ward: str,
        emergency_message: str,
        preferred_channel: Optional[str] = None,
    ) -> AlertDispatch:
        """
        Dispatch triggered by the Emergency Detection Agent (Feature 11).
        Always sends -- an emergency trigger is by definition notify-worthy --
        and defaults to SMS since it needs to reach people who may not have
        the app open.
        """
        channel = preferred_channel or DEFAULT_CHANNEL_BY_BAND["critical"]
        return self._send(recipient=ward, channel=channel, message=emergency_message, risk_level="critical")

    def dispatch_bulk(
        self,
        ward_risk_map: dict,
        message_by_ward: dict,
    ) -> list[AlertDispatch]:
        """
        Convenience batch entry point: given {ward: risk_level} and
        {ward: message} (typically the output of running the Advisory
        Agent across every ward), returns one dispatch per ward that
        clears the notify threshold. Mirrors how a scheduler would call
        this once per ingestion cycle across all wards.
        """
        dispatches = []
        for ward, risk_level in ward_risk_map.items():
            message = message_by_ward.get(ward)
            if not message:
                continue
            dispatch = self.dispatch_advisory(ward, risk_level, message)
            if dispatch:
                dispatches.append(dispatch)
        return dispatches

    @staticmethod
    def _send(recipient: str, channel: str, message: str, risk_level: str) -> AlertDispatch:
        """
        Mock gateway call. Replace this with a real Twilio (SMS/IVR) or
        FCM/APNs (push) call once credentials are available -- callers
        only depend on the returned AlertDispatch shape, not on how the
        send actually happens.
        """
        return AlertDispatch(recipient=recipient, channel=channel, message=message, risk_level=risk_level, status="sent")


if __name__ == "__main__":
    agent = RealTimeAlertAgent()

    print("--- Routine advisory crossing 'poor' band ---")
    d = agent.dispatch_advisory("Ward-3", "poor", "Air quality is poor in Ward-3. Avoid outdoor exercise.")
    print(d)

    print("\n--- Advisory in 'satisfactory' band (should be suppressed) ---")
    d = agent.dispatch_advisory("Ward-1", "satisfactory", "Air quality is acceptable.")
    print(d)

    print("\n--- Emergency-triggered dispatch ---")
    d = agent.dispatch_emergency("Ward-5", "Sudden pollution spike detected in Ward-5 -- PM2.5 jumped sharply in the last 30 minutes.")
    print(d)

    print("\n--- Bulk dispatch across wards ---")
    ward_risk_map = {"Ward-1": "satisfactory", "Ward-2": "very_poor", "Ward-6": "severe"}
    message_by_ward = {
        "Ward-2": "Air quality is very poor in Ward-2. Reduce outdoor activity.",
        "Ward-6": "Air quality is severe in Ward-6. Stay indoors.",
    }
    for d in agent.dispatch_bulk(ward_risk_map, message_by_ward):
        print(d)
