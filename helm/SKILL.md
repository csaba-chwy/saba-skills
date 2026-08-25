---
name: helm
description: Debug Helm-managed applications running in Kubernetes. Use for release, deployment, pod, event, rollout, and log diagnosis; not for unapproved cluster changes.
---

# Helm Kubernetes debugger

Diagnose the requested application with Helm and kubectl, keeping the investigation scoped to the selected Kubernetes context, namespace, workload, and time window. Prefer the smallest read-only query that can answer the question.

## Establish the target

- Treat a Kubernetes **context** and a **namespace** as different things. A context selects a cluster and credentials; never pass a context name as `-n` unless it is also a confirmed namespace.
- Select the AWS SSO profile that matches the target environment: `prd`, `stg`, `qat`, or `dev`. Honor an explicitly supplied profile, but do not guess or fall back between environments. If the context does not make the environment clear, ask the user which profile to use.
- Before contacting an EKS-backed context, authenticate and verify the selected profile: `aws sso login --profile <environment>` followed by `aws sts get-caller-identity --profile <environment>`. If either step fails, report the exact profile and access error and stop for that environment; do not retry with another profile. Run Kubernetes and Helm commands with that same profile, for example `AWS_PROFILE=<environment> kubectl --context <context> ...` and `AWS_PROFILE=<environment> helm --kube-context <context> ...`.
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

## Application logs by environment and region

For a request to read an application's logs given an environment and region:

1. Select the matching AWS profile and locate the configured Kubernetes context containing both the requested environment and region. Confirm the exact context with `kubectl config get-contexts -o name`; do not construct or substitute a context name when there is no match.
2. Discover the application with `AWS_PROFILE=<environment> kubectl --context <context> get deployment -A` or the Helm all-namespace release listing. If it appears in more than one namespace, present the candidates and ask the user to choose one; do not merge logs across namespaces.
3. In the selected namespace, inspect the deployment's labels and pods before choosing a label selector. Read recent logs with the same profile, context, and namespace. If no time window is supplied, begin with `--since=30m --tail=200`, use `--prefix`, and name the container explicitly when the application has more than one. Use `--all-containers=true` only when the container is not yet known and identify the emitting container from the prefix.
4. When a pod has restarted, read its previous container logs separately with `--previous`; keep current and previous output distinct. If there are no matching pods, report the deployment and pod state before widening the search.

For example, after the namespace, selector, and container are confirmed:

```bash
AWS_PROFILE=<environment> kubectl --context <context> logs \
  -n <namespace> -l '<verified-selector>' -c <container> \
  --since=30m --tail=200 --prefix
```

State the profile, context, namespace, selector, containers, and time window used. Return only the decisive, redacted log lines and summarize their pattern; do not return a bulk log dump.

## Explain evidence and stop conditions

Report the exact context, namespace, release or workload, and command-relevant time window. Distinguish observed facts from likely causes, and include the decisive pod condition, event, Helm revision, or short redacted log excerpt. Do not infer that an application is absent from one namespace, one resource type, or an empty Helm query.

Stop once the evidence answers the user’s question. If the evidence points to a corrective action, propose the smallest reversible next action and its expected effect.

## Change boundary

Keep the default workflow read-only. Before `helm upgrade`, `helm rollback`, `helm uninstall`, `kubectl apply`, `edit`, `delete`, `scale`, `rollout restart`, `set image`, or commands run inside a container, summarize the exact target, change, and expected impact and obtain explicit approval. Do not use `--force`, delete workloads to recover a rollout, or expose Secret values as part of diagnosis.
