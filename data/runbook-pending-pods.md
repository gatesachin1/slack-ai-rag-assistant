# Runbook: Pods Stuck in Pending

**Service area:** Kubernetes (Amazon EKS)
**Owner:** Platform SRE team

## Symptoms
- Pod stays in `Pending` state.
- Events show `FailedScheduling` such as "0/3 nodes are available: insufficient cpu" or "node(s) had untolerated taint".

## Common causes
1. Not enough CPU or memory on any node for the pod's requests.
2. Node taints that the pod does not tolerate.
3. `nodeSelector` or affinity rules that match no node.
4. PersistentVolumeClaim cannot bind, or the EBS volume is in a different Availability Zone than the available nodes.
5. The node group has reached its maximum size, so the autoscaler cannot add nodes.
6. The subnet ran out of IP addresses (VPC CNI cannot assign pod IPs).

## Investigation steps
1. `kubectl describe pod <pod>` and read the scheduling message.
2. Check node capacity: `kubectl describe nodes` and `kubectl top nodes`.
3. Check autoscaler logs (Cluster Autoscaler or Karpenter) for scale-up failures.
4. Check PVC status: `kubectl get pvc -n <namespace>`.
5. Check free IPs in the subnets used by the node group.

## Resolution
- Add nodes or increase the node group max size.
- Reduce over-sized resource requests in the Deployment.
- Fix labels, tolerations, or affinity rules.
- Create nodes in the same AZ as the EBS volume.
- Add a secondary CIDR or enable prefix delegation if IP addresses are exhausted.
