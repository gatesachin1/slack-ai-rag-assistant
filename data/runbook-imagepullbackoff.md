# Runbook: Pod in ImagePullBackOff or ErrImagePull

**Service area:** Kubernetes (Amazon EKS), Amazon ECR
**Owner:** Platform SRE team

## Symptoms
- Pod status shows `ImagePullBackOff` or `ErrImagePull`.
- Events show "Failed to pull image" or "pull access denied".

## Common causes
1. Wrong image name or tag (typo, tag does not exist).
2. The image was never pushed because the CI pipeline failed.
3. Node IAM role lacks ECR permissions (`ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`).
4. Private subnet nodes cannot reach ECR (missing NAT Gateway or VPC endpoints for `ecr.api`, `ecr.dkr`, and S3).
5. Image is in a different AWS account or region and no cross-account policy exists.
6. Registry rate limits when pulling from Docker Hub.

## Investigation steps
1. `kubectl describe pod <pod> -n <namespace>` and read the exact error in Events.
2. Confirm the image exists: `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>`
3. Check the node role policies in IAM for ECR read access.
4. From a node or a debug pod, test network reachability to the ECR endpoint.
5. Check the CI pipeline run that was supposed to publish the image.

## Resolution
- Correct the image tag in the Deployment and re-apply.
- Re-run the failed pipeline stage to push the image.
- Attach `AmazonEC2ContainerRegistryReadOnly` to the node role if missing.
- Add VPC interface endpoints for ECR and a gateway endpoint for S3, or fix the NAT route.
- For Docker Hub limits, mirror the image into ECR.

## Verification
Pod reaches `Running` state and the Deployment shows all desired replicas available.
