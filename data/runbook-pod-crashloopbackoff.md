# Runbook: Pod in CrashLoopBackOff

**Service area:** Kubernetes (Amazon EKS)
**Severity guideline:** SEV3 for a single non-critical pod, SEV2 if a customer-facing service has fewer than 50% healthy replicas, SEV1 if the service is fully down.
**Owner:** Platform SRE team

## Symptoms
- `kubectl get pods` shows `CrashLoopBackOff` with a rising RESTARTS count.
- Alert "KubePodCrashLooping" fires in Prometheus.
- Readiness probe failures and reduced replica count on the Deployment.

## Common causes
1. Application error at startup (bad config, missing environment variable, failed dependency connection).
2. Out-of-memory kill (exit code 137, reason `OOMKilled`) because the memory limit is too low.
3. Failing liveness probe that restarts a healthy but slow-starting container.
4. Missing or wrong Secret or ConfigMap reference.
5. Wrong container command or entrypoint after an image change.
6. Permission errors, for example the container runs as a user that cannot write to a mounted volume.

## Investigation steps
1. Identify the failing pod: `kubectl get pods -n <namespace>`
2. Read the events: `kubectl describe pod <pod> -n <namespace>` and check the Last State, Exit Code, and Events sections.
3. Read the logs of the crashed container: `kubectl logs <pod> -n <namespace> --previous`
4. If exit code is 137, check memory usage in Grafana and compare with the memory limit.
5. Check recent changes: `kubectl rollout history deployment/<name> -n <namespace>`
6. Verify that referenced ConfigMaps and Secrets exist: `kubectl get configmap,secret -n <namespace>`

## Resolution
- **Bad release:** roll back with `kubectl rollout undo deployment/<name> -n <namespace>`.
- **OOMKilled:** raise the memory limit and request in the Deployment, then investigate for a memory leak.
- **Probe too aggressive:** increase `initialDelaySeconds` or add a `startupProbe`.
- **Missing config:** create or fix the ConfigMap or Secret, then restart with `kubectl rollout restart deployment/<name>`.

## Verification
- All pods are `Running` and `Ready`.
- Restart count has stopped increasing for at least 15 minutes.
- Error rate and latency on the service dashboard are back to normal.

## Escalation
If the cause is not found within 30 minutes, escalate to the owning application team through the on-call rotation.
