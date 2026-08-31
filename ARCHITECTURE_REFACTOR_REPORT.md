# Architecture Refactor Report

## 1. Before Architecture
- The `LeaveRequestViewSet` was highly bloated (~200 lines). It contained routing logic, permission checks, complex state transition rules, model updating, audit logging, and notification triggering.
- **Problems Found**: 
  - Violates the Single Responsibility Principle (SRP).
  - High risk of race conditions during concurrent approvals because the view fetched the object, modified it in Python memory, and saved it back without database-level locking.

## 2. New Architecture
- Introduced `LeaveService` in `enterprise_hrms/leave_management/services.py`.
- The view now acts purely as an HTTP controller: it extracts request parameters, checks basic permissions, and passes the operation to the Service Layer.

## 3. Benefits
- **Testability**: We can now unit-test `LeaveService.process_manager_approval` completely independently of Django REST Framework request objects.
- **Reusability**: If we introduce a CLI script or a background Celery task to auto-approve certain leaves, it can import `LeaveService` rather than simulating HTTP requests.
- **Code Cleanliness**: The view is significantly shorter and easier to read.
