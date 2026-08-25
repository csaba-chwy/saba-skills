---
name: helm
description: Debug Helm-managed applications running in Kubernetes. Use for release, deployment, pod, event, rollout, and log diagnosis; not for unapproved cluster changes.
---

# Helm Kubernetes debugger

Diagnose the requested application with Helm and kubectl, keeping the investigation scoped to the selected Kubernetes context, namespace, workload, and time window. Prefer the smallest read-only query that can answer the question.

## Establish the target

- Treat a Kubernetes **context** and a **namespace** as different things. A context selects a cluster and credentials; never pass a context name as `-n` unless it is also a confirmed namespace.
- Select the AWS SSO profile that matches the target environment: `prd`, `stg`, `qat`, or `dev`. Honor an explicitly supplied profile, but do not guess or fall back between environments. If the context does not make the environment clear, ask the user which profile to use.
- Before contacting an EKS-backed context, authenticate and verify the selected profile: `aws sso login --profile <environment>` followed by `aws sts get-caller-identity --profile <environment>`. Run Kubernetes and Helm commands with that same profile, for example `AWS_PROFILE=<environment> kubectl --context <context> ...` and `AWS_PROFILE=<environment> helm --kube-context <context> ...`.
- Confirm a supplied context with `kubectl config get-contexts -o name` and include `--context <context>` on every cluster command. If the supplied context is absent, report the available matching contexts and stop for user direction.
- If no namespace is supplied, discover the release or workload across namespaces with `helm --kube-context <context> list --all-namespaces` or `kubectl --context <context> get deployment -A`; once found, use its exact namespace for deeper queries.
- If discovery returns several similarly named workloads or releases, show their namespace, status, and age, then ask the user which is in scope before inspecting logs or manifests.

## Read-only investigation

Start with the user’s concrete symptom. Use only the relevant branch below; do not collect a generic cluster dump.

| Symptom | Read-only evidence |
| --- | --- |
| Release status or recent Helm failure | `helm status`, `helm history`, then namespace events |
| Rollout not completing | Deployment/StatefulSet status, `kubectl rollout status`, `kubectl describe`, and recent events |
| Pods restarting, pending, or failing | Pod status and restarts, targeted `describe pod`, then prior/current container logs |
| Application errors | Identify ready pods through the workload selector and read only the relevant container logs with a bounded `--since` window |
| Incorrect rendered configuration | `helm get manifest` or `helm get values --all`; inspect only non-secret configuration needed for the question |

Use `kubectl get events -n <namespace> --sort-by=.lastTimestamp` for recent scheduling, image-pull, readiness, and controller evidence. For logs, explicitly select the namespace, pod, container when needed, and a short `--since` duration. Use `--previous` only when a container has restarted. Never paste secrets, credentials, authorization headers, tokens, full unredacted environment variables, or Secret data into the response.

When an application label is available, prefer it to a guessed pod name. Helm releases commonly expose `app.kubernetes.io/instance=<release>` and `app.kubernetes.io/name=<application>`; verify labels before relying on them. If Helm reports no release but Kubernetes finds the workload, say that the application was found but Helm ownership was not established.

## Explain evidence and stop conditions

Report the exact context, namespace, release or workload, and command-relevant time window. Distinguish observed facts from likely causes, and include the decisive pod condition, event, Helm revision, or short redacted log excerpt. Do not infer that an application is absent from one namespace, one resource type, or an empty Helm query.

Stop once the evidence answers the user’s question. If the evidence points to a corrective action, propose the smallest reversible next action and its expected effect.

## Change boundary

Keep the default workflow read-only. Before `helm upgrade`, `helm rollback`, `helm uninstall`, `kubectl apply`, `edit`, `delete`, `scale`, `rollout restart`, `set image`, or commands run inside a container, summarize the exact target, change, and expected impact and obtain explicit approval. Do not use `--force`, delete workloads to recover a rollout, or expose Secret values as part of diagnosis.
