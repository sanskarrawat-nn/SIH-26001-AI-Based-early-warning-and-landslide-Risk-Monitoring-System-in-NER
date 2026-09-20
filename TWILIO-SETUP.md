# Twilio WhatsApp crisis alerts

Only this notification feature was added in this update. Existing prediction, map, field reporting and asset workflows remain intact. A separate durable outbox worker sends asynchronously, so a Twilio outage does not fail a prediction request.

## Setup

1. Create a Twilio account and a WhatsApp-enabled sender. For production complete Twilio/Meta sender onboarding. Sandbox testing only reaches recipients who have joined your sandbox; sandbox preapproved templates are not automatically compatible with the crisis template below.
2. In Twilio Content Template Builder create a WhatsApp template and obtain approval. Use this five-variable structure (variable positions matter):

   `Landslide warning: {{1}}. Location: {{2}}. Risk score: {{3}}/100. Action: {{4}}. Alert reference: {{5}}.`

3. Set the following backend environment variables (Render Environment, or backend/.env locally):

```
WHATSAPP_ENABLED=true
TWILIO_ACCOUNT_SID=AC_your_account_sid
TWILIO_AUTH_TOKEN=your_private_token
TWILIO_WHATSAPP_FROM=whatsapp:+your_approved_sender
TWILIO_CONTENT_SID=HX_your_approved_template_sid
OPERATIONS_API_KEY=your_strong_private_admin_key
```

Never put Twilio credentials in frontend code or VITE_ variables. Restart/redeploy the backend. The integration stays inactive if disabled or configuration is incomplete. Keep WHATSAPP_ENABLED=false for development and regression tests.

4. Open Settings > WhatsApp crisis alerts. Enter the deployment access key, click Connect / refresh, then add each person with an international-format phone number, a consent reference and explicit opt-in. Select all monitored locations or a specific location. The application cannot discover arbitrary phone numbers; 'everyone' means the registered opted-in recipients in the selected coverage area. Remove a recipient to opt out and cancel their pending messages.
5. After setup, perform one controlled end-to-end test with an opted-in test phone and verify the delivery in Twilio Console. No real WhatsApp message was sent during development; all provider tests were mocked.

## Behaviour

- Worker checks every 10 seconds while the backend process is running. It only queues HIGH/SEVERE active or acknowledged alerts created within 30 minutes, with a currently high-risk location and source OPEN_METEO_API, MANUAL_INPUT or REAL_SENSOR. Seeded, simulated and unknown sources are excluded; an inactive/free sleeping Render instance cannot run the worker.
- One notification per alert ID, recipient and severity, with a 30-minute same-location/same-severity cooldown to suppress new alert IDs for the same ongoing crisis. Escalation from HIGH to SEVERE generates one additional notification. Registering a recipient can notify them about eligible alerts from the last 30 minutes.
- Messages use Twilio ContentSid and five ContentVariables, so proactive alerts do not depend on an open 24-hour chat session.
- Snapshot queue entries survive restarts. Atomic claims prevent two workers from sending the same queued row. A stopped recipient, resolved alert, changed severity or stale alert cancels pending work.
- Explicit rate-limit rejection and connection-establishment failures retry with backoff, at most five attempts. An ambiguous timeout/server error is UNKNOWN, not automatically resent: review Twilio Console to avoid duplicate delivery. A worker interrupted during submission is also marked UNKNOWN after two minutes.
- Accepted provider messages are polled for sent/delivered/failed status. QUEUED/SENT is not proof of handset delivery. Status polling stops at a terminal delivery result. Refresh the Settings panel to see updates.
- Opt-out cannot retract a message already submitted to Twilio. This is a shared-admin-key integration, not self-service subscriber identity management. Twilio charges and WhatsApp delivery restrictions apply.

## Official references

https://www.twilio.com/docs/whatsapp/tutorial/send-whatsapp-notification-messages-templates
https://www.twilio.com/docs/whatsapp/api
https://www.twilio.com/docs/whatsapp/sandbox
https://www.twilio.com/docs/messaging/api/message-resource

## Deployment note

Upload/deploy this updated source to your existing Render service, configure the variables and register recipients. Downloading the ZIP does not modify the live service. The messaging worker observes operational alerts already produced by the app; it does not add an autonomous weather/sensor polling system.
