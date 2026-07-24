# Jira CLI write runbook

Use the configured Jira CLI for exact reads and writes. In a restricted sandbox, request network escalation for the `jira` command prefix on the first Jira attempt. Do not switch to a browser because a connector credential is missing.

## Preflight

```text
jira me
jira issue view SHOP-123 --plain
jira issue view SHOP-123 --raw
```

The Jira CLI uses the local configuration selected by the user. If discovery fails, pass that locally configured path explicitly. Do not rerun `jira init` or overwrite the configuration for a transient error.

Before a batch, list the exact scope:

```text
jira issue list \
  --jql 'parent = SHOP-98' \
  --order-by key \
  --reverse \
  --plain \
  --no-truncate \
  --columns key,type,status,summary
```

Let the CLI add ordering; do not also embed `ORDER BY` inside JQL.

## Update

Prepare a complete multiline body in a temporary file, then replace the description:

```text
jira issue edit SHOP-123 --no-input < /private/tmp/shop-123-description.md
```

`jira issue edit` replaces the whole description. Retain current content that still matters and pass only fields intended to change. Do not use `--skip-notify` by default; a Jira instance can reject notification suppression even when ordinary writes are allowed.

Use the smallest intended write as the canary. Do not create a dummy issue or comment solely to test access.

## Create

Inspect project and issue-type metadata for required fields before creation. For projects with required custom fields, use the configured display names:

```text
jira issue create \
  -pSHOP \
  -tStory \
  -PSHOP-98 \
  -s'Concise outcome-oriented summary' \
  --template /private/tmp/issue-description.md \
  --custom 'Capitalizable=Yes' \
  --no-input \
  --raw
```

Create Epics with `jira epic create` and Bugs with `jira issue create -tBug`; verify their actual create screens and required custom fields first.

If creation returns HTTP 400, search for the exact summary before retrying. Capture the key from a successful response and immediately read the issue back.

## Parents, links, and workflow

```text
jira issue edit SHOP-123 --parent SHOP-98 --no-input
jira epic remove SHOP-123
jira issue link SHOP-100 SHOP-123 Blocks
jira issue unlink SHOP-100 SHOP-123
jira issue move SHOP-123 "In Progress"
```

Confirm link direction in the raw readback. Do not use an empty `--parent` to clear a parent. Transition only to the exact authorized workflow status; do not silently substitute a terminal state.

## Read-back

After every write:

```text
jira issue view SHOP-123 --plain
jira issue view SHOP-123 --raw
```

Verify the complete description plus key, summary, type, status, parent, assignee, required fields, links, and comments. Treat command exit status plus read-back as authoritative.
