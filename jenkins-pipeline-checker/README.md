# Jenkins Pipeline Checker

Agentic skill for tracing Jenkins-backed GitHub checks to pipeline stages, decisive logs, and reusable CI evidence. Sample usage:

> codex exec "Inspect the failed Jenkins check on this PR, identify the decisive error and owning code, and report the run URL and next action."

The skill diagnoses and reports by default. Code changes, rebuilds, pull-request comments, and Jira updates require the user's authorization.

# Prerequisites

The agent must have network access to the configured Jenkins instance.

Set up your API key as follows:

1. Go to the Jenkins "security" page, for example `https://jenkins.example.com/user/your-name@gmail.com/security/`.
2. Click "Add new token"
3. Give the token a descriptive name like "Codex", and copy it down somewhere safe.
4. Export your username and token to your environment:

```
export JENKINS_USERNAME="myname@gmail.com"
export JENKINS_API_TOKEN="foobar"
```
