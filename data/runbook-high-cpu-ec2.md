# Runbook: High CPU on EC2 Instance

**Service area:** Amazon EC2, Auto Scaling
**Owner:** Platform SRE team

## Symptoms
- CloudWatch alarm: `CPUUtilization` above 85% for 10 minutes.
- Slow response times from the affected service.

## Investigation steps
1. Confirm the trend in CloudWatch (spike, steady rise, or periodic).
2. Connect with SSM Session Manager (do not open SSH to the internet).
3. Identify the process: `top` or `ps aux --sort=-%cpu | head`.
4. Check whether a deployment, cron job, or batch task started at the same time.
5. For burstable instances (T family), check `CPUCreditBalance`. A zero balance throttles the CPU.
6. Check whether the Auto Scaling group is scaling out correctly.

## Resolution
- Stop or reschedule runaway jobs.
- Roll back the release if CPU rose right after deployment.
- Scale out the Auto Scaling group or lower the target tracking threshold.
- Move to a larger or non-burstable instance type if load is consistently high.
- Use AWS Compute Optimizer to right-size instances.

## Escalation
If CPU stays high after scaling and no process explains it, escalate to the application team and consider a security review for unexpected processes such as crypto-miners.
