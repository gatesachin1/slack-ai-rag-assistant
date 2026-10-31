# Runbook: Container OOMKilled

**Service area:** Kubernetes (Amazon EKS)
**Owner:** Platform SRE team

## Symptoms
- Container last state shows `Reason: OOMKilled` and `Exit Code: 137`.
- Pod restarts repeatedly, sometimes under load only.

## Background
A container is killed when it uses more memory than its **limit**. The **request** is used for scheduling, while the **limit** is the hard ceiling. A node can also kill pods when the whole node runs out of memory (node memory pressure eviction), which is different from a container limit kill.

## Investigation steps
1. `kubectl describe pod <pod>` and confirm `OOMKilled`.
2. Compare memory usage with the limit in Grafana (metric `container_memory_working_set_bytes`).
3. Check whether memory grows steadily (likely a leak) or spikes with traffic (limit too low).
4. Check for a recent release that changed memory behavior.
5. For Java apps, verify heap settings such as `-Xmx` are below the container limit.

## Resolution
- Increase the memory limit and request to match real usage plus 20-30% headroom.
- For a leak, roll back the release and open a bug with the owning team.
- Set JVM or runtime memory flags so the runtime respects container limits.
- Consider a Horizontal Pod Autoscaler so load spreads across more pods.

## Prevention
- Always set both requests and limits.
- Add an alert when memory usage exceeds 85% of the limit.
- Load test releases before production.
