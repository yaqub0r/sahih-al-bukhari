# Incident response

1. **Triage:** identify affected release IDs, artifacts, consumers, classifications, and credentials without copying sensitive payloads into public tickets.
2. **Contain:** revoke credentials, restrict access, pause promotion, and move the active pointer to a known safe release when the rollback rules permit it.
3. **Preserve:** retain immutable release evidence and a restricted incident timeline. Do not rewrite a released object.
4. **Correct:** create new record revisions, correction/supersession entries, and a new release closure.
5. **Communicate:** give consumers affected release identities, safe actions, and compatibility impact; do not expose private evidence.
6. **Learn:** update policy, tests, access controls, and recovery exercises. Re-evaluate rights/classification decisions when relevant.

History rewriting, credential rotation, public notification, or legal reporting can have material consequences. Project maintainers must make those decisions using the incident's actual scope and applicable obligations.
