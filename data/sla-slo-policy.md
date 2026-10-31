# SLA, SLO, and Error Budget Policy

**Document owner:** SRE Lead

## Definitions
- **SLI (Service Level Indicator):** a measured value, such as the percentage of successful requests.
- **SLO (Service Level Objective):** the internal target for an SLI, such as 99.9% success over 30 days.
- **SLA (Service Level Agreement):** the contractual promise to customers. SLAs are always looser than SLOs.
- **Error budget:** the amount of unreliability allowed by the SLO. A 99.9% SLO over 30 days allows about 43 minutes of downtime.

## Standard SLOs by tier
| Tier | Services | Availability SLO | Latency SLO (p95) |
|---|---|---|---|
| Tier 1 | Checkout, Payments, Login | 99.95% | under 300 ms |
| Tier 2 | Search, Catalog, Notifications | 99.9% | under 500 ms |
| Tier 3 | Internal tools, Reporting | 99.5% | under 2 s |

## Error budget policy
- **Budget above 50% remaining:** normal release cadence.
- **Budget between 10% and 50%:** releases need extra review and a rollback plan.
- **Budget below 10%:** feature releases are paused. Only reliability fixes and security patches are allowed.
- **Budget exhausted:** release freeze until the 30-day window recovers, and the team must present a reliability improvement plan.

## Alerting principles
- Alert on symptoms that users feel (error rate, latency), not on every internal metric.
- Use **burn-rate alerts**: page when the error budget is being consumed fast (for example 14x burn rate over 1 hour), and open a ticket for slow burns.
- Every paging alert must have a runbook link and an owner.
- Alerts that nobody acts on for 30 days are reviewed and removed or tuned.

## Reporting
SRE publishes a monthly SLO report with attainment, error budget consumption, top incidents, and toil metrics.
