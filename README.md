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
* **`GET /`**: List leave requests (Employees see their own; Department Managers see their department; Admin/HR see all).
* **`POST /`**: Apply for a leave request (Sick, Casual, Annual, Unpaid, etc.). Automatically triggers employee notification.
* **`POST /<id>/manager-approve/`**: Department Manager review step. Body params: `status` (`approve` | `reject`), `comments`. Transitions status to `pending_hr` or `rejected`.
* **`POST /<id>/hr-approve/`**: Final HR review step (Admin/HR only). Body params: `status` (`approve` | `reject`), `comments`. Transitions status to `approved` or `rejected`.

### Payroll Management (`/api/v1/payroll/`)
* **`GET /`**: List payroll records (Restricted to user's own payroll or Admin/HR).
* **`POST /generate/`**: Bulk or single employee payroll generator. Body params: `month`, `year`, optional `employee_id`. Calculates unpaid leave deductions & 10% base allowance.
* **`GET /<id>/slip/`**: Securely stream & download pay slip PDF.

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

