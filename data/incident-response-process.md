# Incident Response Process

**Document owner:** SRE Lead
**Applies to:** All production services at Acme Cloud

## Severity levels
| Level | Definition | Response time | Example |
|---|---|---|---|
| SEV1 | Full outage or data loss affecting most customers | Page immediately, respond within 5 minutes | Checkout service down |
| SEV2 | Major feature degraded for many customers | Respond within 15 minutes | Search very slow, 20% errors |
| SEV3 | Minor issue, workaround exists | Respond within 1 business hour | One report fails to export |
| SEV4 | Cosmetic or low impact | Next business day | UI typo |

## Roles during an incident
- **Incident Commander (IC):** owns the incident, makes decisions, keeps the team focused. Does not debug.
- **Communications Lead:** posts updates to the status page and stakeholders every 30 minutes for SEV1 and every 60 minutes for SEV2.
- **Resolvers:** engineers who investigate and fix.
- **Scribe:** records the timeline in the incident channel.

## Process
1. **Detect:** alert fires or a customer reports an issue.
2. **Acknowledge:** the on-call engineer acknowledges within the response time.
3. **Declare:** for SEV1 and SEV2, open a dedicated Slack channel named `inc-YYYYMMDD-short-name` and start a bridge call.
4. **Assign roles:** the first responder acts as IC until relieved.
5. **Mitigate first:** restore service before finding the root cause. Rollback, failover, or scale out are preferred over live debugging.
6. **Communicate:** post regular updates, even if the update is "no change".
7. **Resolve:** confirm that metrics and SLOs are back to normal.
8. **Postmortem:** hold a blameless postmortem within 5 business days for every SEV1 and SEV2.

## Postmortem requirements
- Timeline of events with timestamps.
- Root cause and contributing factors.
- What went well and what did not.
- Action items with an owner and a due date, tracked in Jira.
- Postmortems are blameless: we fix systems and processes, not blame people.

## Escalation path
1. Primary on-call engineer
2. Secondary on-call engineer (after 15 minutes without acknowledgment)
3. SRE Lead
4. Engineering Director (SEV1 only, or if not resolved in 60 minutes)
