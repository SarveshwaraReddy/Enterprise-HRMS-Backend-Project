# Security Audit & Hardening Report

## 1. Object-Level Authorization (RBAC)
- **Vulnerability**: Employees could potentially access other employees' profiles if object-level filtering was not strictly enforced.
- **Severity**: Critical
- **Fix**: Hardened `get_queryset()` in `EmployeeViewSet` to strictly filter by `user=request.user` for standard roles, ensuring isolation of employee data. Administrators and HR bypass this filter.
- **Test Result**: Passed. Unauthorized access to peer profiles is restricted.

## 2. PII / Sensitive Data Protection in Audit Logs
- **Vulnerability**: Requesting APIs involving passwords or sensitive tokens could leak into audit logs.
- **Severity**: High
- **Fix**: The newly created `AuditMiddleware` exclusively captures `request_id`, `ip_address`, and `user_agent`. Business logic for auditing changes (via the Service layer) selectively logs specific actions, ensuring no plaintext passwords or JWT tokens are written to the `AuditLog` table.
- **Test Result**: Passed.

## 3. Auditing & Traceability
- **Vulnerability**: Lack of non-repudiation for destructive actions.
- **Severity**: Medium
- **Fix**: Implemented `AuditLog` tracking fields: `module`, `model_name`, `object_id`, `old_data`, and `new_data`. All `EmployeeService` actions are now reliably tracked.
- **Test Result**: Passed.
