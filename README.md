# Enterprise HRMS (Human Resource Management System)

A secure, scalable, and feature-rich Django REST Framework (DRF) backend API for managing enterprise human resource workflows, including employee records, departments, attendance logging, leaves, payroll, document uploads, real-time notifications, and audit logs.

---

## Features

1. **User Authentication & Authorization**: Secure signup, JWT authentication, role-based access control (Admin, HR, Employee), and token refresh/blacklisting.
2. **Employee Profile Management**: Comprehensive employee records with uniqueness validations on Email, Phone, and Employee ID, plus role-scoped querysets.
3. **Department Management & Analytics**: Organize employees into departments, track department managers, and fetch aggregate statistics including average salary, total salary budgets, gender distribution, and employee status breakdowns (`/api/v1/departments/<id>/statistics/` & `/api/v1/departments/all_statistics/`).
4. **Attendance Logging**: Clock-in/out tracking with one-record-per-day constraint, automatic check-in/check-out state handling, and monthly summary breakdowns.
5. **Multi-Stage Leave Requests**: Employee application with automated workflow transitions: Department Manager review followed by HR final approval, complete with date validation and status tracking.
6. **Automated Payroll Generator**: Automatic calculation of earnings, default allowances (10% of base), and deduction calculation for unpaid leave days. Generates downloadable, beautifully styled pay slip PDFs.
7. **Secure Document Management**: Private document uploads (Resume, Aadhaar, PAN, certificates) served via a secure streaming endpoint with owner/admin permission checks and automatic disk storage cleanup on file deletion.
8. **Multi-Format Reporting Engine**: Exporters for Employee, Department, Attendance, and Payroll reports supporting CSV, Excel (`.xlsx`), and PDF formats with query filters.
9. **Interactive Dashboard**: Aggregate metrics summary including active employee count, department counts, today's attendance, pending leave requests, current month payroll total, and recent hire lists.
10. **System Audit Logs**: Automatic activity tracking for logins, logouts, employee profile changes, leave approvals, payroll generation, and document access with IP address recording (`/api/v1/audit-logs/`).
11. **In-App Notification Center**: Automated notification triggers on leave submission, manager/HR approvals, and payslip generation. Features endpoints to retrieve notifications, mark individual notifications as read (`/<id>/mark-read/`), and mark all as read (`/mark-all-read/`).
12. **Advanced Search & Filtering**: Standardized query filtering (`filterset_fields`), search (`search_fields`), and ordering (`ordering_fields`) across all primary resources.
13. **Database Seeding Utility**: Pre-configured `seed_data.py` script to instantly populate realistic sample data (users, departments, employees, attendance, leaves, payroll, notifications, and audit logs).
14. **Visual ER Diagram Documentation**: Complete database schema visualization provided via `ER-Diagram( HRMS Enterprise backend system ).png` and `er_diagram.dot`.

---

## Folder Structure

```text
enterprise_hrms_system/
│
├── enterprise_hrms/                # Django Main Package
│   ├── accounts/                   # Authentication & User Model
│   ├── api/                        # Central API Hub (Serializers, Permissions, Custom Exceptions)
│   ├── attendance/                 # Attendance marking & monthly breakdowns
│   ├── audit_logs/                 # Activity tracking & logs
│   ├── dashboard/                  # Aggregate metrics summary & recent lists
│   ├── departments/                # Department CRUD & statistics
│   ├── documents/                  # Secure file upload, download & retrieval
│   ├── employees/                  # Employee profiles management
│   ├── leave_management/           # Multi-stage leave approval workflow
│   ├── notifications/              # Real-time alerts & notification center
│   ├── payroll/                    # Payroll computation & Pay slip PDFs
│   ├── reports/                    # Multi-format report exporter (CSV/Excel/PDF)
│   ├── tests/                      # Consolidated HRMS Test Suite (Auth, Models, APIs, Services)
│   ├── settings.py                 # Django settings
│   ├── urls.py                     # Root routing
│   └── wsgi.py / asgi.py
│
├── media/                          # Media uploads directory (documents, payslips)
├── requirements.txt                # Project dependencies
├── manage.py                       # Django CLI manager
├── seed_data.py                    # Database seeding script
├── README.md                       # Comprehensive documentation
├── POSTMAN_GUIDE.md                # Postman testing guide
├── HRMS_API.postman_collection.json # Ready-to-use Postman collection
├── ER-Diagram( HRMS Enterprise backend system ).png # Schema diagram (PNG)
└── er_diagram.dot                  # Schema diagram (Graphviz DOT format)
```

---

## Installation & Setup

### 1. Prerequisites
* Python 3.10+
* PostgreSQL database server (running on port 5432)

### 2. Clone and Setup Environment
Navigate to the root workspace directory and build a virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Setup
Ensure PostgreSQL is running, then verify database configurations inside `enterprise_hrms/settings.py` under `DATABASES`. Default configuration:
* **Engine**: PostgreSQL (`django.db.backends.postgresql`)
* **Name**: `hrms_portal`
* **User**: `sarveshwarareddy`
* **Port**: `5432`

Apply database migrations to set up tables:
```powershell
python manage.py makemigrations accounts employees departments attendance payroll leave_management documents audit_logs notifications
python manage.py migrate
```

### 4. Database Seeding (Optional)
Populate the database with demo users (Admin, HR, Employees), departments, attendance logs, leave requests, payroll records, notifications, and audit logs:
```powershell
python seed_data.py
```
> **Default Seed Credentials**:
> * **Admin**: `admin@hrms.com` / `Password123!`
> * **HR Manager**: `hr@hrms.com` / `Password123!`
> * **Employee**: `john.doe@hrms.com` / `Password123!`

---

## Running the Application

Start the local development server:
```powershell
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`. You can view the homepage showing available endpoints.

---

## Running Tests

We target 90%+ code coverage. The test suite automatically runs on a fast, self-contained SQLite configuration to avoid database credential conflicts.

Run the test suite:
```powershell
python manage.py test
```

Generate the code coverage report:
```powershell
coverage run --source=enterprise_hrms manage.py test
coverage report -m
```

---

## API Documentation

### Authentication (`/api/v1/auth/`)
* **`POST /register/`**: Register a new user account.
* **`POST /login/`**: Authenticate and retrieve access & refresh JWT tokens.
* **`POST /refresh/`**: Refresh simplejwt access token.
* **`POST /logout/`**: Blacklist refresh token and log out user.
* **`PUT /change-password/`**: Update password for authenticated user.

### Employee Management (`/api/v1/employees/`)
* **`GET /`**: List employee profiles (Employees see their own profile; Admin/HR see all). Supports search & filtering by `department`, `gender`, `status`.
* **`POST /`**: Create a new employee profile (HR/Admin only).
* **`GET /<id>/`**: Retrieve a specific employee profile.
* **`PUT /<id>/`**: Update profile details.
* **`DELETE /<id>/`**: Terminate/delete profile (HR/Admin only).

### Department Management (`/api/v1/departments/`)
* **`GET /`**: List departments.
* **`POST /`**: Create department (HR/Admin only).
* **`GET /<id>/`**: Retrieve department details.
* **`PUT /<id>/`**: Update department (HR/Admin only).
* **`DELETE /<id>/`**: Delete department (HR/Admin only).
* **`GET /<id>/statistics/`**: Aggregate department stats (employee count, salary budget, average salary, status/gender breakdowns).
* **`GET /all_statistics/`**: Aggregated workforce & salary statistics across all departments.

### Attendance Management (`/api/v1/attendance/`)
* **`GET /`**: List attendance records (Filtered by employee for non-admins).
* **`POST /mark/`**: Record employee check-in (first call of the day) or check-out (second call of the day).
* **`GET /monthly/`**: Retrieve monthly attendance breakdown summary. (Query params: `month`, `year`, and optional `employee_id` for HR/Admin).

### Leave Management (`/api/v1/leaves/`)

#### Leave Requests & Approval Workflow
* **`GET /`**: List leave requests (Filtered by ownership / department manager scope / Admin-HR scope).
* **`POST /apply/`**: Apply for a leave request (Body params: `leave_type`, `start_date`, `end_date`, `reason`, optional `is_hr_override`).
* **`GET /my-leaves/`**: Retrieve leave request history for the logged-in employee.
* **`GET /my-balance/`**: Retrieve leave balance breakdown summary for the logged-in employee (Optional query param: `year`).
* **`GET /pending/`**: Retrieve pending leave requests requiring review (Department Managers see department requests; Admin/HR see all pending).
* **`POST /<id>/approve/`** or **`PUT /<id>/approve/`**: Department Manager approval step. Accepts optional `comments`. Transitions status from `pending_manager` to `pending_hr`.
* **`POST /<id>/reject/`** or **`PUT /<id>/reject/`**: Manager or HR rejection step. Accepts optional `comments`. Transitions status to `rejected`.
* **`POST /<id>/final-approve/`** or **`PUT /<id>/final-approve/`**: HR final approval step (Admin/HR only). Accepts optional `comments`. Transitions status to `approved` and updates employee leave balance.
* **`POST /<id>/cancel/`** or **`PUT /<id>/cancel/`**: Cancel a leave request. Accepts optional `reason`. Restores leave balance if previously approved.

#### Leave Types Management (`/api/v1/leaves/types/`)
* **`GET /types/`**: List all configured leave types (Sick, Casual, Annual, Unpaid, etc.).
* **`POST /types/`**: Create a new leave type (Admin/HR only).
* **`GET /types/<id>/`**: Retrieve leave type details.
* **`PUT /types/<id>/`**: Update leave type properties (Admin/HR only).
* **`DELETE /types/<id>/`**: Delete leave type (Admin/HR only).

#### Leave Balances (`/api/v1/leaves/balances/`)
* **`GET /balances/`**: List leave balances (Employees see their own balance; Admin/HR see all. Query params: `employee`, `year`, `leave_type`).
* **`GET /balances/<id>/`**: Retrieve a specific leave balance record.

#### Leave Calendar & Schedules (`/api/v1/leaves/calendar/`)
* **`GET /calendar/monthly/`**: Monthly leave calendar view (Query params: `month`, `year`).
* **`GET /calendar/team/`**: Team leave calendar view (Optional query param: `department_id`).
* **`GET /calendar/upcoming/`**: List upcoming leaves starting today or in the future.
* **`GET /calendar/currently-on-leave/`**: List employees currently on approved leave today.

#### Leave Analytics & Reporting (`/api/v1/leaves/analytics/` & `/api/v1/leaves/report/`)
* **`GET /analytics/`**: Detailed leave analytics summary (Most used leave types, monthly trends, average leave days per employee, zero balance list). Restricted to Admin/HR.
* **`GET /report/`**: Export leave reports in PDF, Excel (`.xlsx`), or CSV formats (Query params: `report_format` = `pdf`|`excel`|`csv`, `report_type` = `history`|`annual_register`|`dept_summary`|`transactions`). Restricted to Admin/HR.

### Payroll Management (`/api/v1/payroll/`)
* **`GET /`**: List payroll records (Restricted to user's own payroll or Admin/HR).
* **`POST /generate/`**: Bulk or single employee payroll generator. Body params: `month`, `year`, optional `employee_id`. Calculates unpaid leave deductions & 10% base allowance.
* **`GET /<id>/slip/`**: Securely stream & download pay slip PDF.

### Enterprise Payroll Engine & Workflow (`/api/v1/payroll/`)

#### Salary Structure Management (`/api/v1/payroll/salary-structure/`)
* **`POST /api/v1/payroll/salary-structure/`**: Create employee salary structure (Basic, HRA, Special, Travel, Medical allowances; PF, Professional Tax, Income Tax, Other deductions; Effective Date, Status). Restricted to Admin/HR.
* **`GET /api/v1/payroll/salary-structure/`**: List salary structures (Filtered by `employee` or `status`).
* **`PUT /api/v1/payroll/salary-structure/<id>/`**: Update existing salary structure.
* **`DELETE /api/v1/payroll/salary-structure/<id>/`**: Delete salary structure record.

#### Monthly Payroll Processing & Workflow (`/api/v1/payroll/run/`)
* **`POST /api/v1/payroll/run/`**: Create & initialize monthly payroll run (`payroll_month`, `payroll_year`, `remarks`). Automatically integrates attendance & approved leave to calculate gross, LWP deductions, overtime pay, and net salary for active employees. Enforces single run per month rule.
* **`GET /api/v1/payroll/run/`**: List monthly payroll runs.
* **`PUT /api/v1/payroll/run/<id>/approve/`**: Approve a draft/processing payroll run. Enforces manager/HR approval rule.
* **`PUT /api/v1/payroll/run/<id>/release/`**: Release approved payroll run. Notifies employees and seals the run as immutable.

#### Payslip Management & Download (`/api/v1/payroll/payslips/`)
* **`GET /api/v1/payroll/payslips/`**: List payslips. Restricted to own payslips for Employees; all for Admin/HR.
* **`GET /api/v1/payroll/payslips/<id>/`**: View specific payslip details and breakdown.
* **`GET /api/v1/payroll/payslips/<id>/download/`**: Stream & download PDF payslip featuring company branding, earnings/deductions table, attendance summary, and embedded verification QR Code.

#### Payroll Dashboard & Analytics (`/api/v1/payroll/dashboard/`)
* **`GET /api/v1/payroll/dashboard/`**: Retrieve real-time payroll metrics (Current Payroll Status, Employees Processed, Pending Payslips, Total Payroll Cost, Department Salary Summary).

#### Payroll Reports & Multi-Format Exports (`/api/v1/payroll/reports/`)
* **`GET /api/v1/payroll/reports/summary/`**: Payroll summary report (Total employees paid, gross payroll, total deductions, net payroll).
* **`GET /api/v1/payroll/reports/department/`**: Department payroll report (Payroll by department, average, highest, lowest salary).
* **`GET /api/v1/payroll/reports/history/`**: Employee salary history by month (Query param: `employee_id`).
* **`GET /api/v1/payroll/reports/export/`**: Export payroll reports in PDF, Excel (`.xlsx`), or CSV formats (Query params: `format` = `pdf`|`excel`|`csv`, `month`, `year`).

### Secure Document Management (`/api/v1/documents/`)
* **`GET /`**: List uploaded employee documents.
* **`POST /`**: Upload credentials file (Resume, Aadhaar, PAN, certificates).
* **`GET /<id>/download/`**: Stream secure file download. Validates owner or Admin/HR permissions.
* **`DELETE /<id>/`**: Delete document and automatically remove file from server disk storage.

### Notification Center (`/api/v1/notifications/`)
* **`GET /`**: List notifications for logged-in user. Query param filter: `is_read` (`true` | `false`).
* **`POST /<id>/mark-read/`**: Mark a specific notification as read.
* **`POST /mark-all-read/`**: Mark all notifications for logged-in user as read.

### Audit Logs (`/api/v1/audit-logs/`)
* **`GET /`**: View activity audit log history (Admin/HR only). Supports search and filters by `user`, `action`, `ip_address`.
* **`GET /<id>/`**: View specific audit log details.

### Reports Engine (`/api/v1/reports/`)
Exporters for CSV, Excel (`.xlsx`), and PDF. Restricted to Admin/HR.
* **`GET /employees/`**: Export employee report. Query params: `report_format` (`csv`|`excel`|`pdf`), `department_id`, `status`.
* **`GET /departments/`**: Export department report. Query param: `report_format`.
* **`GET /attendance/`**: Export attendance report. Query params: `report_format`, `start_date`, `end_date`, `employee_id`.
* **`GET /payroll/`**: Export payroll report. Query params: `report_format`, `month`, `year`.

### Dashboard (`/api/v1/dashboard/`)
* **`GET /`**: Summary metrics (active employees, departments, today's attendance, pending leave requests, current month payroll total, recent hires).

---

## API Collection & Postman Guide

* **Postman Collection**: Import `HRMS_API.postman_collection.json` directly into Postman to test and interact with all endpoints.
* **Postman Testing Guide**: Refer to `POSTMAN_GUIDE.md` for step-by-step instructions on authentication flows, automatic token persistence, role testing, file uploads, and sample requests.
* **Database ER Diagram**: See `ER-Diagram( HRMS Enterprise backend system ).png` or `er_diagram.dot` for visual database schema representation.

---

## 💼 Payroll System — Complete Operations Guide

The Payroll module implements a full enterprise-grade payroll pipeline covering salary structure management, monthly processing, attendance integration, payslip generation, multi-level approvals, analytics, and multi-format exports.

All payroll endpoints are prefixed with: **`/api/v1/payroll/`**

> **Authentication**: All endpoints require a valid Bearer JWT token in the `Authorization` header.
> ```
> Authorization: Bearer <access_token>
> ```

---

### 🔐 Role & Permission Matrix

| Operation | Employee | HR | Admin / Superuser |
|---|:---:|:---:|:---:|
| View own salary structure | ❌ | ✅ | ✅ |
| Create / update salary structure | ❌ | ✅ | ✅ |
| Delete salary structure | ❌ | ✅ | ✅ |
| Create payroll run | ❌ | ✅ | ✅ |
| Approve payroll run | ❌ | ✅ | ✅ |
| Release payroll run | ❌ | ✅ | ✅ |
| View own payslips | ✅ | ✅ | ✅ |
| Download own payslip PDF | ✅ | ✅ | ✅ |
| View all payslips | ❌ | ✅ | ✅ |
| View payroll dashboard | ❌ | ✅ | ✅ |
| Payroll summary report | ❌ | ✅ | ✅ |
| Department payroll report | ❌ | ✅ | ✅ |
| View own salary history | ✅ | ✅ | ✅ |
| Export payroll (PDF/Excel/CSV) | ❌ | ✅ | ✅ |

---

### 📐 Salary Calculation Formulas

```
Gross Salary  =  Basic Salary
               + House Rent Allowance (HRA)
               + Special Allowance
               + Medical Allowance
               + Travel Allowance

Base Deductions =  Provident Fund (PF)
                 + Professional Tax
                 + Income Tax (TDS)
                 + Other Deductions

LWP Deduction  =  (Gross Salary ÷ Working Days) × Leave Without Pay Days

Overtime Pay   =  (Gross Salary ÷ (Working Days × 8)) × 1.5 × Overtime Hours

Net Salary     =  max(0,  Gross Salary + Overtime Pay
                         − Base Deductions − LWP Deduction)
```

> **Business Rule**: Net salary is always floored at `₹0.00` — it can never be negative.

---

### ⚙️ Payroll Workflow

```
HR / Admin
    │
    ▼
[1] Create Salary Structure   →  POST /salary-structure/
    │
    ▼
[2] Create Payroll Run        →  POST /run/
    │  (auto-fetches attendance & approved leaves,
    │   calculates salary for ALL active employees,
    │   generates payslip PDFs)
    ▼
[3] Review Payslips           →  GET  /payslips/
    │
    ▼
[4] Manager / HR Approval     →  PUT  /run/{id}/approve/
    │
    ▼
[5] Release Payroll           →  PUT  /run/{id}/release/
    │  (notifies employees, seals run as immutable)
    ▼
[6] Employee Downloads PDF    →  GET  /payslips/{id}/download/
```

---

### 1️⃣ Salary Structure Management

#### Create Salary Structure
```http
POST /api/v1/payroll/salary-structure/
```

**Request Body:**
```json
{
  "employee": 5,
  "basic_salary": "45000.00",
  "house_rent_allowance": "18000.00",
  "special_allowance": "5000.00",
  "travel_allowance": "3000.00",
  "medical_allowance": "1250.00",
  "provident_fund": "5400.00",
  "professional_tax": "200.00",
  "income_tax": "3500.00",
  "other_deductions": "0.00",
  "effective_from": "2026-01-01",
  "status": "active"
}
```

**Response `201 Created`:**
```json
{
  "id": 12,
  "employee": 5,
  "employee_name": "Alice Smith (EMP101)",
  "basic_salary": "45000.00",
  "house_rent_allowance": "18000.00",
  "special_allowance": "5000.00",
  "travel_allowance": "3000.00",
  "medical_allowance": "1250.00",
  "provident_fund": "5400.00",
  "professional_tax": "200.00",
  "income_tax": "3500.00",
  "other_deductions": "0.00",
  "effective_from": "2026-01-01",
  "status": "active",
  "gross_salary": "72250.00",
  "total_deductions": "9100.00",
  "net_salary": "63150.00",
  "created_at": "2026-08-04T05:30:00Z",
  "updated_at": "2026-08-04T05:30:00Z"
}
```

> **Auto-deactivation**: Creating a new `active` salary structure automatically deactivates all previous active structures for that employee.

---

#### List Salary Structures
```http
GET /api/v1/payroll/salary-structure/
```

| Query Parameter | Type | Description |
|---|---|---|
| `employee` | integer | Filter by employee ID |
| `status` | string | `active` or `inactive` |
| `search` | string | Search by employee name / ID |

---

#### Update Salary Structure
```http
PUT /api/v1/payroll/salary-structure/{id}/
```

Send only the fields you want to change. All decimal fields are supported.

```json
{
  "basic_salary": "50000.00",
  "income_tax": "4000.00"
}
```

---

#### Delete Salary Structure
```http
DELETE /api/v1/payroll/salary-structure/{id}/
```

**Response `204 No Content`** — record permanently removed.

---

### 2️⃣ Monthly Payroll Processing

#### Create Payroll Run
```http
POST /api/v1/payroll/run/
```

**Request Body:**
```json
{
  "payroll_month": 8,
  "payroll_year": 2026,
  "remarks": "August 2026 payroll run"
}
```

**Response `201 Created`:**
```json
{
  "id": 7,
  "payroll_month": 8,
  "payroll_year": 2026,
  "status": "draft",
  "processed_by": 2,
  "processed_by_email": "hr@company.com",
  "processed_at": "2026-08-04T06:00:00Z",
  "approved_by": null,
  "approved_by_email": null,
  "approved_at": null,
  "remarks": "August 2026 payroll run",
  "total_payslips": 42,
  "created_at": "2026-08-04T06:00:00Z",
  "updated_at": "2026-08-04T06:00:00Z"
}
```

**Business Rules enforced:**
- ❌ Only **one** payroll run per `month + year` combination allowed
- ❌ Employees without an active salary structure are skipped (not an error)
- ✅ Attendance records and approved leaves are automatically included in calculation

---

#### List Payroll Runs
```http
GET /api/v1/payroll/run/
```

| Query Parameter | Type | Description |
|---|---|---|
| `payroll_month` | integer | Filter by month (1–12) |
| `payroll_year` | integer | Filter by year |
| `status` | string | `draft`, `processing`, `approved`, `released` |

---

#### Approve Payroll Run
```http
PUT /api/v1/payroll/run/{id}/approve/
```
*(Also accepts `POST`)*

**Response `200 OK`:**
```json
{
  "id": 7,
  "status": "approved",
  "approved_by": 2,
  "approved_by_email": "hr@company.com",
  "approved_at": "2026-08-04T08:00:00Z"
}
```

**Business Rules enforced:**
- ❌ Cannot approve a **released** payroll run
- ✅ Sets `approved_by`, `approved_at`, and transitions status to `approved`

---

#### Release Payroll Run
```http
PUT /api/v1/payroll/run/{id}/release/
```
*(Also accepts `POST`)*

**Response `200 OK`:**
```json
{
  "id": 7,
  "status": "released"
}
```

**Business Rules enforced:**
- ❌ Cannot release a run that is **not yet approved**
- ✅ Transitions status to `released` (immutable — no further modifications allowed)
- ✅ Sends in-app notifications to all employees with their net salary

---

### 3️⃣ Payslip Operations

#### List Payslips
```http
GET /api/v1/payroll/payslips/
```

| Query Parameter | Type | Description |
|---|---|---|
| `employee` | integer | Filter by employee ID (HR/Admin only) |
| `payroll_run` | integer | Filter by payroll run ID |
| `payroll_run__payroll_month` | integer | Filter by month |
| `payroll_run__payroll_year` | integer | Filter by year |
| `search` | string | Search by employee name / ID |

> **Permission scoping**: Employees see only their own payslips. HR/Admin see all.

---

#### View Payslip Detail
```http
GET /api/v1/payroll/payslips/{id}/
```

**Response `200 OK`:**
```json
{
  "id": 83,
  "employee": 5,
  "employee_id_code": "EMP101",
  "employee_name": "Alice Smith (EMP101)",
  "employee_details": { ... },
  "department_name": "Engineering",
  "payroll_run": 7,
  "payroll_month": 8,
  "payroll_year": 2026,
  "payroll_status": "released",
  "gross_salary": "72250.00",
  "total_deductions": "9800.00",
  "net_salary": "62450.00",
  "working_days": 31,
  "present_days": "29.0",
  "leave_days": "2.0",
  "overtime_hours": "0.00",
  "pdf_path": "payslips/payslip_EMP101_8_2026.pdf",
  "generated_at": "2026-08-04T06:01:15Z"
}
```

---

#### Download Payslip PDF
```http
GET /api/v1/payroll/payslips/{id}/download/
```

**Response**: Binary PDF stream with headers:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="payslip_EMP101_8_2026.pdf"
```

**PDF Contents:**
- 🏢 Company name & address header
- 🔲 QR code for verification (encodes employee ID, period, net salary)
- 👤 Employee information (ID, name, department, designation, email)
- 📅 Payroll month / year
- 📊 Attendance summary (working days, present days, leave days, overtime hours)
- 💰 Earnings & Deductions breakdown table
- ✅ Net salary payable highlighted box
- ✍️ Employee & Authorized signatory fields

> **Auto-regeneration**: If the PDF file is missing from disk, it is regenerated on-the-fly and saved before being returned.

---

### 4️⃣ Payroll Dashboard
```http
GET /api/v1/payroll/dashboard/
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "current_payroll_status": "released",
    "latest_payroll_run": {
      "id": 7,
      "month": 8,
      "year": 2026,
      "status": "released"
    },
    "employees_processed": 42,
    "pending_payslips": 0,
    "total_payroll_cost": "2621900.00",
    "department_payroll_summary": [
      {
        "department_id": 1,
        "department_name": "Engineering",
        "employee_count": 15,
        "total_payroll": "980000.00",
        "avg_salary": "65333.33",
        "highest_salary": "95000.00",
        "lowest_salary": "45000.00"
      }
    ]
  }
}
```

---

### 5️⃣ Payroll Reports

#### Payroll Summary Report
```http
GET /api/v1/payroll/reports/summary/
```

| Query Parameter | Type | Description |
|---|---|---|
| `month` | integer | Filter by month |
| `year` | integer | Filter by year |

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "total_employees_paid": 42,
    "gross_payroll": "3035450.00",
    "total_deductions": "413550.00",
    "net_payroll": "2621900.00"
  }
}
```

#### Department Payroll Report
```http
GET /api/v1/payroll/reports/department/
```

| Query Parameter | Type | Description |
|---|---|---|
| `month` | integer | Filter by month |
| `year` | integer | Filter by year |

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "department_id": 1,
      "department_name": "Engineering",
      "employee_count": 15,
      "total_payroll": "980000.00",
      "avg_salary": "65333.33",
      "highest_salary": "95000.00",
      "lowest_salary": "45000.00"
    },
    {
      "department_id": 2,
      "department_name": "HR",
      "employee_count": 8,
      "total_payroll": "420000.00",
      "avg_salary": "52500.00",
      "highest_salary": "70000.00",
      "lowest_salary": "38000.00"
    }
  ]
}
```

#### Employee Salary History
```http
GET /api/v1/payroll/reports/history/
```

| Query Parameter | Type | Description |
|---|---|---|
| `employee_id` | integer | Employee ID (HR/Admin can query any; Employee queries own) |

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "payslip_id": 83,
      "month": 8,
      "year": 2026,
      "status": "released",
      "gross_salary": "72250.00",
      "total_deductions": "9800.00",
      "net_salary": "62450.00",
      "working_days": 31,
      "present_days": "29.0",
      "generated_at": "2026-08-04T06:01:15Z"
    },
    {
      "payslip_id": 61,
      "month": 7,
      "year": 2026,
      "status": "released",
      "gross_salary": "72250.00",
      "total_deductions": "9400.00",
      "net_salary": "62850.00",
      "working_days": 31,
      "present_days": "31.0",
      "generated_at": "2026-07-04T06:01:15Z"
    }
  ]
}
```

---

### 6️⃣ Export Payroll Reports

All exports are available via:
```http
GET /api/v1/payroll/reports/export/
```

| Query Parameter | Type | Required | Description |
|---|---|---|---|
| `export_format` | string | ✅ | `pdf`, `excel`, or `csv` |
| `month` | integer | ❌ | Target month (defaults to latest run) |
| `year` | integer | ❌ | Target year (defaults to latest run) |

#### Export as PDF
```http
GET /api/v1/payroll/reports/export/?export_format=pdf&month=8&year=2026
```
Returns a styled, paginated PDF with payroll summary header and full employee payroll table.
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="payroll_report_8_2026.pdf"
```

#### Export as Excel
```http
GET /api/v1/payroll/reports/export/?export_format=excel&month=8&year=2026
```
Returns an `.xlsx` workbook (`Payroll Register` sheet) with styled headers, all employee payroll rows, and grid borders.
```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="payroll_register_8_2026.xlsx"
```

**Excel columns:** Employee ID | Employee Name | Department | Designation | Month/Year | Working Days | Present Days | Gross Salary | Total Deductions | Net Salary | Status

#### Export as CSV
```http
GET /api/v1/payroll/reports/export/?export_format=csv&month=8&year=2026
```
Returns a flat CSV with all payroll transactions.
```
Content-Type: text/csv
Content-Disposition: attachment; filename="payroll_transactions_8_2026.csv"
```

**CSV columns:** Payslip ID | Employee ID | Employee Name | Email | Department | Month | Year | Gross Salary | Total Deductions | Net Salary | Working Days | Present Days | Leave Days | Generated At

---

### 7️⃣ Legacy Payroll (Backward Compatible)

#### Generate Payroll (Legacy)
```http
POST /api/v1/payroll/generate/
```

**Request Body:**
```json
{
  "month": 8,
  "year": 2026,
  "employee_id": 5
}
```

> Omitting `employee_id` generates payroll for **all active employees**.
> Uses simplified calculation: 10% allowance, unpaid leave deduction only.

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Successfully generated payroll for 1 employee(s).",
  "data": [
    {
      "id": 14,
      "employee": 5,
      "month": 8,
      "year": 2026,
      "basic_salary": "45000.00",
      "allowances": "4500.00",
      "deductions": "3000.00",
      "net_salary": "46500.00",
      "status": "generated"
    }
  ]
}
```

#### Download Legacy Payslip PDF
```http
GET /api/v1/payroll/{id}/slip/
```

Returns PDF stream for the legacy `Payroll` record.

---

### 🔔 Payroll Notifications

When a payroll run is **released**, all processed employees automatically receive an in-app notification:

```
Title: "Payroll Released"
Message: "Your payslip for 8/2026 has been released. Net Salary: $62,450.00"
```

Employees can view notifications at:
```http
GET /api/v1/notifications/
```

---

### ❌ Common Error Responses

| Scenario | Status Code | Message |
|---|---|---|
| Duplicate payroll run for same month | `400` | `"A payroll run for 8/2026 already exists."` |
| Release before approval | `400` | `"Payroll cannot be released before it is approved."` |
| Modify released payroll | `400` | `"Released payroll cannot be modified or reprocessed."` |
| Employee has no salary structure | `400` | `"Salary structure must exist for employee '...' before payroll generation."` |
| Employee not found | `404` | `"Employee with ID X not found."` |
| Payroll run not found | `404` | `"Payroll run with ID X not found."` |
| Insufficient permissions | `403` | `"You do not have permission to perform this action."` |
| Unauthenticated request | `401` | `"Authentication credentials were not provided."` |

---

### 🧪 Running Payroll Tests

```powershell
# Run all payroll module tests
python manage.py test enterprise_hrms.payroll.tests --verbosity=2

# Run with coverage report
coverage run --source=enterprise_hrms.payroll manage.py test enterprise_hrms.payroll.tests
coverage report --include="enterprise_hrms/payroll/*" --omit="*/migrations/*"
```

**Test Coverage Results (91 tests):**

| Test File | Tests | Coverage |
|---|---|---|
| `test_models.py` | 16 | Models, properties, constraints |
| `test_services.py` | 31 | Service layer, calculations, validators, reports |
| `test_api.py` | 28 | All REST endpoints + edge cases |
| `test_permissions.py` | 16 | Role enforcement for all operations |
| **Total** | **91** | **98% code coverage** |

---

## 💻 Asset Management Module

The **Asset Management** module tracks physical hardware, software licenses, maintenance schedules, and IT support ticketing.

### Key Operations & Capabilities

**1. Asset Inventory Management (Admins & IT Staff)**
- Manage asset categories (Laptops, Monitors, Phones, etc.).
- Maintain a complete inventory of physical assets with unique codes, vendor details, purchase dates, and warranty tracking.
- *Endpoints:* `GET /api/v1/assets/`, `POST /api/v1/assets/`, `GET /api/v1/assets/categories/`

**2. Asset Assignment (Admins & IT Staff)**
- Assign assets to specific employees (tracks assigned date and expected return).
- Process returned assets, automatically marking them as "Available" again.
- Employees can view their currently assigned assets.
- *Endpoints:* `POST /api/v1/assets/assign/`, `PUT /api/v1/assets/return/`, `GET /api/v1/assets/my-assets/`

**3. Asset Maintenance (Admins & IT Staff)**
- Schedule preventative maintenance or repairs for assets (changes status to "Under Maintenance").
- Mark maintenance as completed (returns status to "Available") and track maintenance costs.
- *Endpoints:* `POST /api/v1/assets/{id}/schedule-maintenance/`, `POST /api/v1/assets/maintenance/{id}/complete/`

**4. Software Licenses (Admins & IT Staff)**
- Track software licenses, subscription types, and keys.
- Assign licenses to employees and revoke them when necessary.
- Monitor upcoming license expirations (next 30 days).
- *Endpoints:* `GET /api/v1/assets/licenses/`, `PUT /api/v1/assets/licenses/{id}/assign/`, `GET /api/v1/assets/licenses/expiring-soon/`

**5. IT Support Ticketing (All Employees)**
- Employees can open IT support tickets linked to specific assets and categories.
- IT Staff and Admins can assign tickets to specific engineers.
- IT Staff and Admins can resolve and close tickets with resolution notes.
- *Endpoints:* `POST /api/v1/assets/support/tickets/`, `PUT /api/v1/assets/support/tickets/{id}/assign/`, `PUT /api/v1/assets/support/tickets/{id}/close/`

**6. Reporting & Dashboard**
- Export inventory, support, and license data to PDF, Excel, and CSV formats.
- View a high-level dashboard summarizing asset statuses, open tickets, and maintenance requests.
- *Endpoints:* `GET /api/v1/assets/dashboard/`, `GET /api/v1/assets/reports/assets/?format=pdf`

### 🧪 Running Asset Management Tests

The Asset Management module includes **106 tests** with comprehensive coverage.

```powershell
# Run all asset management tests
python manage.py test enterprise_hrms.asset_management --verbosity=2
```

