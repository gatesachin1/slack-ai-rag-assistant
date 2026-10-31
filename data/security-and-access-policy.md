# Security and Access Policy

**Document owner:** Security Team

## Access principles
- **Least privilege:** users and services get only the permissions they need.
- **No long-lived keys:** workloads use IAM roles (instance profiles, IRSA, or EKS Pod Identity). Static access keys are not allowed in code, CI variables, or container images.
- **MFA is mandatory** for all console and SSO logins.
- Production access is granted through temporary, time-limited roles and is logged in CloudTrail.

## Secrets management
- Secrets are stored in AWS Secrets Manager or SSM Parameter Store, never in Git.
- Secrets are rotated every 90 days. Database credentials rotate automatically.
- A secret found in a repository is treated as compromised and must be rotated immediately.

## Network security
- Only load balancers are public. Application servers and nodes live in private subnets.
- Security groups allow traffic only from the required source security groups. No `0.0.0.0/0` on SSH or database ports.
- Use SSM Session Manager instead of SSH or bastion hosts.
- AWS WAF is attached to every internet-facing ALB and CloudFront distribution.

## Data protection
- Encryption at rest with KMS for S3, EBS, and RDS.
- Encryption in transit with TLS 1.2 or higher.
- S3 buckets block public access by default.

## Kubernetes security
- RBAC roles are namespace-scoped. Developers have edit access in dev and qa and read-only access in prod.
- CI/CD pipelines authenticate with IAM roles mapped through EKS access entries.
- Pods run as non-root where possible, and images are scanned in the pipeline.

## Monitoring and response
- GuardDuty, CloudTrail, and Security Hub are enabled in all accounts.
- Security findings of HIGH or CRITICAL severity must be triaged within 24 hours.
