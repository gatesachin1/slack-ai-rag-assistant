# Runbook: ALB Returning 5xx Errors

**Service area:** AWS Application Load Balancer, EKS Ingress
**Owner:** Platform SRE team

## Symptoms
- CloudWatch alarm on `HTTPCode_ELB_5XX_Count` or `HTTPCode_Target_5XX_Count`.
- Users see 502, 503, or 504 errors.

## Meaning of each code
- **502 Bad Gateway:** the target closed the connection or sent an invalid response. Often the app crashed or keep-alive timeout on the app is shorter than the ALB idle timeout (default 60 seconds).
- **503 Service Unavailable:** no healthy targets are registered.
- **504 Gateway Timeout:** the target did not respond within the ALB idle timeout.
- **500 from target:** the application itself returned an error. Check application logs.

## Investigation steps
1. Check target group health in the console or with `aws elbv2 describe-target-health`.
2. Compare `HTTPCode_ELB_5XX_Count` (problem at the load balancer) with `HTTPCode_Target_5XX_Count` (problem in the app).
3. Check `TargetResponseTime` for latency spikes.
4. Check recent deployments, since 502 and 503 often appear during a bad rollout.
5. Review ALB access logs in S3 for the failing paths and target IPs.
6. Check security groups: the target security group must allow traffic from the ALB security group on the application port.

## Resolution
- Roll back a faulty deployment.
- Fix the health check path or port so healthy pods are marked healthy.
- Increase the application keep-alive timeout above the ALB idle timeout.
- Scale out targets if the cause is overload.
- For 504, find the slow dependency (database, downstream API) and fix or raise timeouts carefully.
