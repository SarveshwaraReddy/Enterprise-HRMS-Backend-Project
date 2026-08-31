# Code Optimization Report

## 1. ORM Optimization
- **Identified Issues**: The `EmployeeViewSet` had N+1 query issues because it was fetching the `user` and `department` fields lazily for every employee in the list.
- **Resolution**: Updated `get_queryset()` in `enterprise_hrms/employees/views.py` to use `select_related('department', 'user')`. This reduced the number of queries for a list of employees from `O(N)` to `O(1)`.

## 2. Refactoring & Code Quality
- **Identified Issues**: Business logic (e.g., audit logging) was tightly coupled within the Django views (`perform_create`, `perform_update`, `perform_destroy`).
- **Resolution**: Introduced a Service Layer (`enterprise_hrms/employees/services.py`). The view now delegates creation, updating, and deletion to `EmployeeService`, adhering to the Single Responsibility Principle (SRP) and making testing easier.

## 3. Global Pagination
- **Identified Issues**: APIs were capable of returning all database records at once, causing memory bloat and slow API responses.
- **Resolution**: Implemented and configured `CustomPagination` globally in `settings.py` with a default `PAGE_SIZE` of 20, capping the max records returned per request.
