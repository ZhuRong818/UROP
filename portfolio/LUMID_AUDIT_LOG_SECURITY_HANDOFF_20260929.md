# Sanitized Lumid audit-log credential exposure handoff

Date: 29 September 2026. A researcher reports that an error field in `lumid_data_meta.audit_log` contains a plaintext database connection string with a password. The affected audit event is dated 13 May 2026. The actual string and password are intentionally omitted here; inspect the reported row through a restricted incident channel. This report is based on the researcher's observation and has not been independently queried by EventX.

Requested owner actions:

1. Confirm the row and identify the credential owner and whether it is still valid. Rotate it promptly if valid or its status is uncertain.
2. Restrict access to, and remediate, the credential-bearing audit error and any copies or exports. Preserve necessary incident evidence in a restricted location.
3. Review how error text entered the API audit log, redact connection strings/passwords before persistence, and check related error rows for the same pattern without exporting secrets into ordinary reports.
4. Review access to the affected log and record the remediation and impact assessment.

This issue is separate from V6 feed-window and market-status certification. No raw credential appears in this handoff, and no external message has been sent.
