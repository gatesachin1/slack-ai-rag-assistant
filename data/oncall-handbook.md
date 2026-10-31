# On-Call Handbook

**Document owner:** SRE Lead

## Schedule
- Rotation is weekly, handover every Monday at 10:00 IST.
- There is a primary and a secondary on-call engineer.
- Engineers can swap shifts through the on-call tool, with notice to the SRE Lead.

## Expectations
- Acknowledge pages within 5 minutes for SEV1 and within 15 minutes for SEV2.
- Keep a laptop and stable internet access available during the shift.
- Do not make risky production changes alone during an incident. Ask the secondary or the IC.
- Write handover notes at the end of the shift covering open incidents, flaky alerts, and pending actions.

## Tools
- **Prometheus and Grafana:** metrics and dashboards.
- **CloudWatch:** AWS service metrics and logs.
- **Datadog:** APM and traces for Tier 1 services.
- **Slack:** the `#incidents` channel for declarations and updates.
- **Jira:** tickets and postmortem action items.
- **Confluence:** runbooks and documentation.

## First 10 minutes of a page
1. Acknowledge the alert.
2. Open the linked runbook.
3. Check the service dashboard and recent deployments.
4. Decide on severity. If SEV1 or SEV2, declare an incident.
5. Mitigate: rollback, scale out, or fail over.

## Reducing toil
Any manual task done more than twice a month should be automated. Track toil in Jira with the label `toil` and review it in the monthly SRE meeting.

## Compensation and rest
Engineers who handle a SEV1 overnight get the next morning off. On-call allowance is paid per week of rotation.
