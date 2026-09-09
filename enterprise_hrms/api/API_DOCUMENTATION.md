# Enterprise HRMS API Documentation

This project exposes the API under the base path:

```text
/api/v1/
```

## Authentication and common usage

- All protected endpoints require the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

- JWT login returns `access` and `refresh` tokens.
- `refresh` is used to rotate access tokens.
- `logout` blacklists the refresh token.
- Most list and detail APIs use DRF serializers and return JSON payloads.
- For document upload, use `multipart/form-data` instead of JSON.

---

## 1. Authentication APIs

Base route: `/api/v1/auth/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | Register a new account | Public |
| POST | `/api/v1/auth/login/` | Login and receive JWT tokens | Public |
| POST | `/api/v1/auth/refresh/` | Refresh a JWT access token | Public |
| POST | `/api/v1/auth/logout/` | Invalidate refresh token | Authenticated |
| PUT | `/api/v1/auth/change-password/` | Change current user password | Authenticated |

### 1.1 Register

Request body:

```json
{
  "username": "jdoe",
  "email": "jdoe@example.com",
  "phone": "+1234567890",
  "role": "employee",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!"
}
```

Notes:
- `password` is validated with Django password validators.
- `password_confirm` must match exactly.
- Default role is `employee` if omitted.

### 1.2 Login

Request body:

```json
{
  "email": "jdoe@example.com",
  "password": "StrongPass123!"
}
```

Example success response:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>",
  "user": {
    "id": 5,
    "email": "jdoe@example.com",
    "username": "jdoe",
    "role": "employee"
  }
}
```

### 1.3 Refresh token

Request body:

```json
{
  "refresh": "<refresh_token>"
}
```

### 1.4 Logout

Request body:

```json
{
  "refresh": "<refresh_token>"
}
```

### 1.5 Change password

Request body:

```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!",  
  "new_password_confirm": "NewPass456!"
}
```

---

## 2. Employee Management APIs

Base route: `/api/v1/employees/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/employees/` | List employees | Authenticated |
| POST | `/api/v1/employees/` | Create an employee profile | Admin/HR |
| GET | `/api/v1/employees/{id}/` | Get employee details | Authenticated |
| PUT | `/api/v1/employees/{id}/` | Full update | Authenticated with permission |
| PATCH | `/api/v1/employees/{id}/` | Partial update | Authenticated with permission |
| DELETE | `/api/v1/employees/{id}/` | Delete employee | Admin/HR |

### 2.1 Create employee

Request body:

```json
{
  "employee_id": "EMP-1001",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567891",
  "dob": "1990-05-14",
  "gender": "male",
  "department": 1,
  "designation": "Software Engineer",
  "salary": 75000.00,
  "joining_date": "2024-01-10",
  "status": "active",
  "user": 5
}
```

Notes:
- `department` is a department ID.
- `gender` accepts `male`, `female`, or `other`.
- `status` accepts `active`, `inactive`, `terminated`, or `on_leave`.
- Employees can only view their own profile unless they are admin/HR.

### 2.2 Update employee

Request body:

```json
{
  "designation": "Senior Software Engineer",
  "salary": 90000.00,
  "status": "active"
}
```

### 2.3 Query filters

Common query params:

```text
?department=1
&gender=male
&status=active
&search=john
&ordering=employee_id
```

---

## 3. Department Management APIs

Base route: `/api/v1/departments/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/departments/` | List departments | Authenticated |
| POST | `/api/v1/departments/` | Create department | Admin/HR |
| GET | `/api/v1/departments/{id}/` | Get department details | Authenticated |
| PUT | `/api/v1/departments/{id}/` | Update department | Admin/HR |
| PATCH | `/api/v1/departments/{id}/` | Partial update | Admin/HR |
| DELETE | `/api/v1/departments/{id}/` | Delete department | Admin/HR |
| GET | `/api/v1/departments/{id}/statistics/` | Department salary and workforce stats | Authenticated |
| GET | `/api/v1/departments/all_statistics/` | Aggregate all department stats | Authenticated |

### 3.1 Create department

Request body:

```json
{
  "name": "Engineering",
  "code": "ENG",
  "manager": 12,
  "description": "Core software and product engineering team"
}
```

Notes:
- `code` must be unique.
- `manager` is an employee ID.

### 3.2 Department statistics

Endpoint:

```text
GET /api/v1/departments/1/statistics/
```

Response shape:

```json
{
  "department_id": 1,
  "department_name": "Engineering",
  "department_code": "ENG",
  "total_employees": 12,
  "average_salary": 85000.0,
  "total_salary_budget": 1020000.0,
  "status_breakdown": {
    "active": 10,
    "on_leave": 1,
    "inactive": 1
  },
  "gender_breakdown": {
    "male": 8,
    "female": 4
  }
}
```

---

## 4. Attendance Management APIs

Base route: `/api/v1/attendance/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/attendance/` | List attendance records | Authenticated |
| POST | `/api/v1/attendance/` | Manually create attendance object | Authenticated with permission |
| GET | `/api/v1/attendance/{id}/` | Get one attendance record | Authenticated |
| PUT | `/api/v1/attendance/{id}/` | Update attendance | Authenticated with permission |
| PATCH | `/api/v1/attendance/{id}/` | Partial update | Authenticated with permission |
| DELETE | `/api/v1/attendance/{id}/` | Delete attendance | Admin/HR |
| POST | `/api/v1/attendance/mark/` | Check in/check out for logged-in employee | Authenticated |
| GET | `/api/v1/attendance/monthly/` | Monthly attendance summary | Authenticated |

### 4.1 Manual attendance create

Request body:

```json
{
  "employee": 5,
  "date": "2026-08-31",
  "check_in": "09:00:00",
  "check_out": "18:00:00",
  "status": "present"
}
```

Notes:
- `employee` is required.
- `check_out` must be after `check_in`.
- One attendance record per employee per date is enforced.

### 4.2 Mark attendance

Endpoint:

```text
POST /api/v1/attendance/mark/
```

No body is required. The server uses the logged-in employee profile to determine check-in/check-out for the current date.

Example responses:

```json
{
  "success": true,
  "message": "Checked in successfully.",
  "data": {
    "id": 22,
    "employee": 5,
    "employee_name": "John Doe",
    "employee_id_code": "EMP-1001",
    "date": "2026-08-31",
    "check_in": "09:15:00",
    "check_out": null,
    "status": "present"
  }
}
```

### 4.3 Monthly summary

Endpoint:

```text
GET /api/v1/attendance/monthly/?month=8&year=2026
```

For Admin/HR, include the employee ID:

```text
GET /api/v1/attendance/monthly/?month=8&year=2026&employee_id=5
```

Response:

```json
{
  "success": true,
  "data": {
    "employee_id": 5,
    "employee_name": "John Doe",
    "month": 8,
    "year": 2026,
    "total_days_logged": 22,
    "breakdown": {
      "present": 20,
      "absent": 1,
      "late": 1,
      "half_day": 0
    }
  }
}
```

---

## 5. Leave Management APIs

Base route: `/api/v1/leaves/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/leaves/` | List leave requests | Authenticated |
| POST | `/api/v1/leaves/` | Submit leave request | Authenticated |
| GET | `/api/v1/leaves/{id}/` | Get leave request | Authenticated |
| PUT | `/api/v1/leaves/{id}/` | Update leave request | Authenticated with permission |
| PATCH | `/api/v1/leaves/{id}/` | Partial update | Authenticated with permission |
| DELETE | `/api/v1/leaves/{id}/` | Delete leave request | Authenticated with permission |
| POST | `/api/v1/leaves/{id}/manager-approve/` | Manager approval/rejection | Department manager / Admin / HR |
| POST | `/api/v1/leaves/{id}/hr-approve/` | Final HR approval/rejection | Admin / HR |

### 5.1 Apply for leave

Request body:

```json
{
  "leave_type": "casual",
  "reason": "Family function",
  "start_date": "2026-09-10",
  "end_date": "2026-09-12"
}
```

Notes:
- `leave_type` values: `sick`, `casual`, `annual`, `maternity`, `paternity`, `unpaid`.
- `end_date` must be greater than or equal to `start_date`.
- For employee users, the system automatically uses the logged-in employee profile.

### 5.2 Manager approval

Endpoint:

```text
POST /api/v1/leaves/15/manager-approve/
```

Request body:

```json
{
  "status": "approve",
  "comments": "Approved for the requested dates."
}
```

Valid values for `status` are:
- `approve`
- `reject`

### 5.3 HR approval

Endpoint:

```text
POST /api/v1/leaves/15/hr-approve/
```

Request body:

```json
{
  "status": "approve",
  "comments": "Final approval granted."
}
```

---

## 6. Payroll Management APIs

Base route: `/api/v1/payroll/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/payroll/` | List payroll records | Authenticated |
| POST | `/api/v1/payroll/` | Manually create payroll | Admin/HR |
| GET | `/api/v1/payroll/{id}/` | Get payroll details | Authenticated |
| PUT | `/api/v1/payroll/{id}/` | Update payroll | Admin/HR |
| PATCH | `/api/v1/payroll/{id}/` | Partial update | Admin/HR |
| DELETE | `/api/v1/payroll/{id}/` | Delete payroll | Admin/HR |
| POST | `/api/v1/payroll/generate/` | Generate payroll for month/year | Admin/HR |
| GET | `/api/v1/payroll/{id}/slip/` | Download payslip PDF | Employee owner / Admin / HR |

### 6.1 Manual payroll create

Request body:

```json
{
  "employee": 5,
  "month": 8,
  "year": 2026,
  "basic_salary": 80000.00,
  "allowances": 8000.00,
  "deductions": 1500.00,
  "status": "generated"
}
```

Notes:
- `basic_salary` must be greater than `0`.
- `allowances` and `deductions` cannot be negative.
- `net_salary` is recalculated automatically as `basic_salary + allowances - deductions`.

### 6.2 Bulk payroll generation

Endpoint:

```text
POST /api/v1/payroll/generate/
```

Request body:

```json
{
  "month": 8,
  "year": 2026,
  "employee_id": 5
}
```

Notes:
- `employee_id` is optional.
- If omitted, all active employees are included.
- The backend automatically applies unpaid leave deductions.
- Allowances default to `10%` of the employee salary.

### 6.3 Payslip download

Endpoint:

```text
GET /api/v1/payroll/12/slip/
```

This returns a PDF file attachment.

---

## 7. Document Management APIs

Base route: `/api/v1/documents/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/documents/` | List documents | Authenticated |
| POST | `/api/v1/documents/` | Upload employee document | Authenticated |
| GET | `/api/v1/documents/{id}/` | Get document metadata | Authenticated |
| PUT | `/api/v1/documents/{id}/` | Update document record | Authenticated with permission |
| PATCH | `/api/v1/documents/{id}/` | Partial update | Authenticated with permission |
| DELETE | `/api/v1/documents/{id}/` | Delete document and file | Authenticated with permission |
| GET | `/api/v1/documents/{id}/download/` | Download the stored file | Owner / Admin / HR |

### 7.1 Upload document

Endpoint:

```text
POST /api/v1/documents/
```

Form-data body:

```text
employee: 5
document_type: resume
file: <binary file>
```

Supported values for `document_type`:
- `resume`
- `aadhaar`
- `pan`
- `certificate`

Notes:
- Use `multipart/form-data`.
- If the logged-in user is an employee, the system auto-assigns the employee profile.

### 7.2 Download document

Endpoint:

```text
GET /api/v1/documents/3/download/
```

This returns the actual file as an attachment.

---

## 8. Notification APIs

Base route: `/api/v1/notifications/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/notifications/` | List notifications for logged-in user | Authenticated |
| GET | `/api/v1/notifications/{id}/` | Get one notification | Authenticated |
| POST | `/api/v1/notifications/{id}/mark-read/` | Mark a single notification as read | Authenticated |
| POST | `/api/v1/notifications/mark-all-read/` | Mark all notifications as read | Authenticated |

### 8.1 Mark all read

Endpoint:

```text
POST /api/v1/notifications/mark-all-read/
```

Body is usually empty.

### 8.2 Mark one read

Endpoint:

```text
POST /api/v1/notifications/10/mark-read/
```

Body is usually empty.

---

## 9. Audit Log APIs

Base route: `/api/v1/audit-logs/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/audit-logs/` | View audit trail | Admin/HR |
| GET | `/api/v1/audit-logs/{id}/` | View a specific audit log | Admin/HR |

This module records actions such as:
- login/logout events
- profile changes
- leave approvals
- payroll generation
- file downloads
- IP address and metadata tracking

No request body is required for list or detail endpoints.

---

## 10. Report Export APIs

Base route: `/api/v1/reports/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/reports/employees/` | Export employee report | Admin/HR |
| GET | `/api/v1/reports/departments/` | Export department report | Admin/HR |
| GET | `/api/v1/reports/attendance/` | Export attendance report | Admin/HR |
| GET | `/api/v1/reports/payroll/` | Export payroll report | Admin/HR |

### 10.1 Employee report example

```text
GET /api/v1/reports/employees/?department_id=1&status=active&report_format=excel
```

Supported `report_format` values:
- `csv` (default)
- `excel`
- `pdf`

### 10.2 Attendance report example

```text
GET /api/v1/reports/attendance/?start_date=2026-08-01&end_date=2026-08-31&report_format=pdf
```

### 10.3 Payroll report example

```text
GET /api/v1/reports/payroll/?month=8&year=2026&report_format=csv
```

These endpoints return the generated file as a download attachment.

---

## 11. Dashboard APIs

Base route: `/api/v1/dashboard/`

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/v1/dashboard/` | Dashboard summary | Admin/HR |

Example response:

```json
{
  "success": true,
  "message": "Dashboard data retrieved successfully.",
  "data": {
    "total_employees": 120,
    "active_employees": 108,
    "departments": 9,
    "attendance_today": 95,
    "pending_leaves": 12,
    "payroll_this_month": 420000.0,
    "recent_employees": [
      {
        "id": 15,
        "employee_id": "EMP-1015",
        "first_name": "Aisha",
        "last_name": "Khan",
        "designation": "QA Analyst",
        "joining_date": "2026-08-01",
        "status": "active"
      }
    ]
  }
}
```

---

## 12. Notes and implementation details

- Base URL for all APIs: `/api/v1/`
- Authenticated requests should include JWT access tokens.
- Some endpoints are custom action routes, such as `mark`, `monthly`, `manager-approve`, `hr-approve`, `generate`, `slip`, `download`, and `mark-all-read`.
- Role rules are controlled by custom permission classes:
  - Admin/HR can manage most records.
  - Employees can usually only access their own data.
  - Department managers can approve leaves for their department employees.

This documentation reflects the actual backend implementation in the project, including the request bodies and query parameters that the API expects.
