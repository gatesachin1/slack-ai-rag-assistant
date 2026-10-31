# FAQ: New Engineer Onboarding

**Q: How do I get access to the AWS accounts?**
Raise a Jira ticket in the IT-ACCESS project with your manager's approval. Access is granted through AWS SSO with read-only permissions by default. Elevated access is time-limited.

**Q: How do I connect to the EKS cluster?**
Run `aws eks update-kubeconfig --name <cluster-name> --region us-east-1` after logging in with SSO. Your IAM role must be mapped to Kubernetes through an EKS access entry.

**Q: Which namespaces exist?**
`dev`, `qa`, and `prod` for applications, plus `kube-system` for core components and `monitoring` for Prometheus and Grafana.

**Q: How do I deploy my service?**
Merge to the develop branch to deploy to dev automatically. Promotion to qa is automatic after tests pass. Production needs a manual approval in the pipeline.

**Q: Where do I find dashboards?**
Grafana has one dashboard per service, named `<service>-overview`. Tier 1 services also have APM traces in Datadog.

**Q: Where are the runbooks?**
All runbooks are in the Confluence space called SRE-Runbooks. Every paging alert links to its runbook.

**Q: How do I request a new AWS resource?**
Infrastructure is created only through Terraform. Open a pull request in the `infra-live` repository and request a review from the platform team.

**Q: What is the policy on using AI tools?**
Approved AI tools may be used for drafting code, scripts, and documentation. Never paste secrets, customer data, or private keys into any AI tool. All AI-generated code must be reviewed and tested before use.

**Q: Who do I contact for urgent production issues?**
Page the on-call engineer through the on-call tool, and post in the `#incidents` Slack channel.

**Q: How are costs tracked?**
Every resource must have the tags `Environment`, `Project`, and `Owner`. Untagged resources are reported weekly and may be removed.
