# Jenkins Pipeline Checker

Agentic skill to facilitate interaction with Jenkins (especially reading logs and triggering builds.) Sample usage:

> codex exec "Look at my branch's Jenkins build. Figure out why it's broken. Fix it. Push to origin. Wait for the build to finish. If it fails, rinse and repeat. If it succeeds, you're done."

The agent will realize you're trying to fiddle with Jenkins builds, match to this skill, and start interacting with Jenkins builds.

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
