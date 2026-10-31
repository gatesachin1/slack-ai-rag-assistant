# Deployment and Rollback Policy

**Document owner:** Platform Engineering

## Principles
- Build once, deploy many: the same container image is promoted through dev, QA, and prod.
- Every production change goes through the CI/CD pipeline. No manual changes on servers.
- Infrastructure changes are made through Terraform pull requests, never in the console.

## Environments
| Environment | Purpose | Deployment trigger |
|---|---|---|
| dev | Developer testing | Automatic on merge to the develop branch |
| qa | Integration and regression testing | Automatic after dev checks pass |
| prod | Customers | Manual approval required |

## Pre-deployment checklist
1. Pull request reviewed and approved by at least one peer.
2. Unit, integration, and security scan stages are green.
3. Image scanned for critical vulnerabilities.
4. Database changes are backward compatible (expand, migrate, contract).
5. Rollback plan documented in the change ticket.
6. Change window approved. Avoid Fridays and peak traffic hours.
7. On-call engineer informed.

## Deployment strategies
- **Rolling update:** default for stateless services.
- **Blue-green:** used for Tier 1 services where instant rollback is required.
- **Canary:** used for risky changes. Start with 5% of traffic, then 25%, 50%, and 100% if error rate and latency stay within SLO.
- **Feature flags:** used to release code without exposing the feature.

## Post-deployment validation
1. Run smoke tests.
2. Watch error rate, latency, and saturation dashboards for 30 minutes.
3. Check logs for new error patterns.
4. Confirm with QA or the product owner.
5. Close the change ticket.

## Rollback
- Rollback is triggered when error rate exceeds the SLO threshold, health checks fail, or a critical bug is found.
- Kubernetes: `kubectl rollout undo deployment/<name>`.
- Helm: `helm rollback <release> <revision>`.
- Blue-green: switch traffic back to the previous environment.
- Rollback decisions do not need management approval. The on-call engineer can roll back immediately.

## Last-minute change requests during a release
Changes requested during a go-live are not accepted unless they are critical. Non-critical requests wait for the next release. Critical requests need a quick review, testing, and approval from the Release Manager.
