# Leave Management Postman Operations Guide

This document details all API operations, request formats, query parameters, permissions, and testing workflows for the **Leave Management** module in Postman.

---

## 📁 Files Included

- **Postman Collection JSON**: [`postman_collection.json`](file:///c:/Users/DELL/Desktop/enterpise_hrms_system/enterprise_hrms/leave_management/postman_collection.json)  
  *(Import directly into Postman via `Import` -> `File` -> select `postman_collection.json`)*

---

## 🔑 Base Configuration & Variables

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `base_url` | `http://127.0.0.1:8000` | Backend API server URL |
| `token` | `""` | JWT Access Token (Auto-populated on Login) |
| `leave_id` | `1` | ID of the leave request for operation testing |
| `leave_type_id` | `1` | ID of the leave type for configuration testing |
| `balance_id` | `1` | ID of the leave balance record |

> **Authorization Header**: All requests except authentication require:
> `Authorization: Bearer {{token}}`

---

## 📋 Summary of Operations in Postman

### 1. Authentication
* **Get Bearer Access Token**: `POST {{base_url}}/api/v1/auth/login/`

### 2. Leave Types Management (Admin / HR)
* **List Leave Types**: `GET {{base_url}}/api/v1/leaves/types/`
* **Create Leave Type**: `POST {{base_url}}/api/v1/leaves/types/`
* **Retrieve Leave Type**: `GET {{base_url}}/api/v1/leaves/types/{{leave_type_id}}/`
* **Update Leave Type**: `PUT {{base_url}}/api/v1/leaves/types/{{leave_type_id}}/`
* **Partial Update Leave Type**: `PATCH {{base_url}}/api/v1/leaves/types/{{leave_type_id}}/`
* **Delete Leave Type**: `DELETE {{base_url}}/api/v1/leaves/types/{{leave_type_id}}/`

### 3. Leave Balances
* **List All Leave Balances**: `GET {{base_url}}/api/v1/leaves/balances/`
* **Filter Leave Balances**: `GET {{base_url}}/api/v1/leaves/balances/?employee=1&year=2026&leave_type=1`
* **Retrieve Balance Details**: `GET {{base_url}}/api/v1/leaves/balances/{{balance_id}}/`

### 4. Employee Leave Operations
* **Apply for Leave**: `POST {{base_url}}/api/v1/leaves/apply/`
* **My Leave History**: `GET {{base_url}}/api/v1/leaves/my-leaves/`
* **My Balance Summary**: `GET {{base_url}}/api/v1/leaves/my-balance/?year=2026`
* **Cancel Leave Request**: `POST {{base_url}}/api/v1/leaves/{{leave_id}}/cancel/`

### 5. Leave Request CRUD Operations
* **List All Leave Requests**: `GET {{base_url}}/api/v1/leaves/?status=pending_manager&search=John`
* **Create Leave Request**: `POST {{base_url}}/api/v1/leaves/`
* **Retrieve Leave Request**: `GET {{base_url}}/api/v1/leaves/{{leave_id}}/`
* **Update Leave Request**: `PUT {{base_url}}/api/v1/leaves/{{leave_id}}/`
* **Delete Leave Request**: `DELETE {{base_url}}/api/v1/leaves/{{leave_id}}/`

### 6. Multi-Level Approval Workflow
* **List Pending Requests**: `GET {{base_url}}/api/v1/leaves/pending/`
* **Manager Approve Leave (Stage 1)**: `POST {{base_url}}/api/v1/leaves/{{leave_id}}/approve/`
* **Reject Leave Request**: `POST {{base_url}}/api/v1/leaves/{{leave_id}}/reject/`
* **HR Final Approve Leave (Stage 2)**: `POST {{base_url}}/api/v1/leaves/{{leave_id}}/final-approve/`

### 7. Leave Calendar APIs
* **Monthly Leave Calendar**: `GET {{base_url}}/api/v1/leaves/calendar/monthly/?month=8&year=2026`
* **Team Leave Calendar**: `GET {{base_url}}/api/v1/leaves/calendar/team/?department_id=1`
* **Upcoming Leaves**: `GET {{base_url}}/api/v1/leaves/calendar/upcoming/`
* **Currently On Leave Today**: `GET {{base_url}}/api/v1/leaves/calendar/currently-on-leave/`

### 8. Analytics & Report Exporters (Admin / HR)
* **Leave Analytics Summary**: `GET {{base_url}}/api/v1/leaves/analytics/?year=2026`
* **Export PDF History Report**: `GET {{base_url}}/api/v1/leaves/report/?report_format=pdf&report_type=history`
* **Export Excel Annual Register**: `GET {{base_url}}/api/v1/leaves/report/?report_format=excel&report_type=annual_register`
* **Export Excel Department Summary**: `GET {{base_url}}/api/v1/leaves/report/?report_format=excel&report_type=dept_summary`
* **Export CSV Transactions**: `GET {{base_url}}/api/v1/leaves/report/?report_format=csv&report_type=transactions`

---

## 🛠 Detailed Endpoint Specifications & Request Payloads

### 1. Login (Get Bearer Token)
- **Method**: `POST`
- **URL**: `{{base_url}}/api/v1/auth/login/`
- **Body**:
```json
{
  "email": "john.doe@hrms.com",
  "password": "Password123!"
}
```
- **Postman Test Script**:
```javascript
var jsonData = pm.response.json();
if (jsonData.access) {
    pm.collectionVariables.set('token', jsonData.access);
    console.log('Access token saved:', jsonData.access);
}
```

---

### 2. Apply for Leave (Employee)
- **Method**: `POST`
- **URL**: `{{base_url}}/api/v1/leaves/apply/`
- **Headers**: `Authorization: Bearer {{token}}`, `Content-Type: application/json`
- **Body**:
```json
{
  "leave_type": "CL",
  "start_date": "2026-08-10",
  "end_date": "2026-08-12",
  "reason": "Attending family function in hometown.",
  "is_hr_override": false
}
```
- **Response**: `201 Created` with initial status `"pending_manager"`.

---

### 3. Manager Approval (Stage 1)
- **Method**: `POST` or `PUT`
- **URL**: `{{base_url}}/api/v1/leaves/{{leave_id}}/approve/`
- **Headers**: `Authorization: Bearer {{token}}`
- **Body**:
```json
{
  "comments": "Approved by department manager. Forwarded to HR."
}
```
- **Response**: `200 OK` with status updated to `"pending_hr"`.

---

### 4. HR Final Approval (Stage 2)
- **Method**: `POST` or `PUT`
- **URL**: `{{base_url}}/api/v1/leaves/{{leave_id}}/final-approve/`
- **Headers**: `Authorization: Bearer {{token}}`
- **Body**:
```json
{
  "comments": "Final approval granted by HR."
}
```
- **Response**: `200 OK` with status updated to `"approved"` and leave balance automatically updated.

---

### 5. Cancel Leave Request
- **Method**: `POST` or `PUT`
- **URL**: `{{base_url}}/api/v1/leaves/{{leave_id}}/cancel/`
- **Headers**: `Authorization: Bearer {{token}}`
- **Body**:
```json
{
  "reason": "Plans changed, leave no longer required."
}
```
- **Response**: `200 OK` with status updated to `"cancelled"`. If previously approved, restores remaining days in leave balance.

---

### 6. Create Leave Type (HR / Admin)
- **Method**: `POST`
- **URL**: `{{base_url}}/api/v1/leaves/types/`
- **Headers**: `Authorization: Bearer {{token}}`
- **Body**:
```json
{
  "name": "Maternity Leave",
  "code": "ML",
  "annual_quota": 90,
  "is_paid": true,
  "description": "Paid maternity leave quota for eligible employees."
}
```

---

### 7. Export Reports (Admin / HR)
- **Method**: `GET`
- **URL**: `{{base_url}}/api/v1/leaves/report/`
- **Query Params**:
  - `report_format`: `pdf` | `excel` | `csv`
  - `report_type`: `history` | `annual_register` | `dept_summary` | `transactions`
- **Example**: `GET {{base_url}}/api/v1/leaves/report/?report_format=excel&report_type=annual_register`

---

## 🔄 End-to-End Testing Workflow in Postman

1. **Login**:
   - Send `Login (Get JWT Token)` as Employee (`john.doe@hrms.com`).
   - Token is automatically saved to `{{token}}`.

2. **Check Current Balance**:
   - Send `My Leave Balance Summary`.

3. **Submit Leave Request**:
   - Send `Apply for Leave`. Note the `id` returned in response and set variable `{{leave_id}}`.

4. **Manager Review**:
   - Send `Login` as Department Manager (`hr@hrms.com` or manager user).
   - Send `List Pending Manager Approvals` to verify the request.
   - Send `Manager Approve Leave (Stage 1)` using `{{leave_id}}`.

5. **HR Final Approval**:
   - Send `Login` as HR Manager (`hr@hrms.com`).
   - Send `HR Final Approve Leave (Stage 2)`.

6. **Verify Calendar & Analytics**:
   - Send `Monthly Leave Calendar`, `Currently On Leave Today`, and `Leave Analytics Summary`.

7. **Export Report**:
   - Send `Export Leave Report (PDF History)` or `Export Leave Report (Excel Annual Register)`.
