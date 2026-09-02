# Epic creation

Jira creates against a project key, not a board name. Inspect the target project's Epic create metadata and a recent representative Epic before drafting the write plan; required fields can differ within the same Jira instance. Do not infer Waffle fields from another project or send them to a project whose metadata does not expose them.

## Keep every field concise

- Use the Epic name and summary for the outcome.
- Keep the Description to a short outcome/ownership paragraph and one to three acceptance criteria.
- Make `flash-report-summary` one sentence about current intent or status; do not copy the Description.
- Make `project-goal-and/or-learning-objective` one sentence with the intended measurable outcome or learning.
- Use `YYYY-MM-DD` dates, an exact configured team/health option, and the shortest honest LOE value. Ask for missing values rather than inventing them.
- Send the Description directly with `--body`; for multiline content, use `--template -` and provide it on standard input. Do not persist Jira content in session-specific or shared temporary files.

## Waffle-configured Epic profile

PDP Epic creation was verified on 2026-08-24 with this complete required set:

| Field | CLI input |
| --- | --- |
| Epic name | `--name` |
| Summary | `--summary` |
| Description | `--body` or `--template -` via standard input |
| SFW Scrum Team | `--custom sfw-scrum-team=<exact option>` |
| Start Date | `--custom start-date=YYYY-MM-DD` |
| Target Date | `--custom target-date=YYYY-MM-DD` |
| Health | `--custom health=<exact option>` |
| Capitalizable | `--custom capitalizable=Yes\|No` |
| LOE | `--custom loe=<concise estimate>` |
| Flash Report Summary | `--custom flash-report-summary=<one sentence>` |
| Project Goal and/or Learning Objective | `--custom 'project-goal-and/or-learning-objective=<one sentence>'` |

The slash in `project-goal-and/or-learning-objective` is part of the configured alias. Preserve it. Example shape after approval:

```text
jira epic create -pPDP \
  -n'Concise capability' \
  -s'Concise capability' \
  --body 'Deliver the concise outcome within the stated ownership boundary.' \
  --custom 'sfw-scrum-team=Product Detail Page' \
  --custom 'start-date=2026-08-24' \
  --custom 'target-date=2026-09-30' \
  --custom 'health=⚪ Gray' \
  --custom 'capitalizable=No' \
  --custom 'loe=TBD' \
  --custom 'flash-report-summary=Deliver the approved outcome within the target window.' \
  --custom 'project-goal-and/or-learning-objective=Establish the intended measurable outcome.' \
  --no-input
```

Treat the example values as syntax only. Use approved values supported by the target project's metadata.

## Non-Waffle comparison

O11Y Epic creation was verified on 2026-08-24 to require `capitalizable` but none of the other PDP/Waffle fields. Still provide a concise Description when it makes the outcome executable:

```text
jira epic create -pO11Y \
  -n'Concise capability' \
  -s'Concise capability' \
  --body 'Deliver the concise outcome within the stated ownership boundary.' \
  --custom 'capitalizable=No' \
  --no-input
```

When metadata differs from these verified examples, the current metadata wins. Include every required field and no irrelevant custom fields in the Jira write plan, then read back the created Epic and verify its type, summary, description, and submitted custom fields.
