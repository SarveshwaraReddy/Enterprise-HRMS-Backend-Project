# Python Advanced Refactoring

This document describes 5 Python functions from the HRMS application that were refactored using advanced Python concepts, decorators, context managers, and modern design patterns.

## 1. `process_manager_approval` (Leave Management)
**Before:**
```python
@staticmethod
@transaction.atomic
def process_manager_approval(leave_id, decision, comments, approver_profile, request_obj):
    leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
    if leave_req.status != 'pending_manager':
        raise ValueError("Leave request is not in a valid state for manager approval.")
    # ... modifies data, logs action, and creates notification
```
**Problem:**
- Uses generic `ValueError` instead of domain-specific exceptions.
- Passes a long list of parameters rather than a single structured data object.
- Business validation, logging, and database transactions are intertwined in the core logic.

**Refactoring:**
- Introduced a `LeaveApprovalDTO` using `@dataclass` to encapsulate parameters.
- Replaced `ValueError` with `InvalidWorkflowStateError`.
- Moved logging to an `@audit_action` decorator and timing to `@execution_timing`.
- Wrapped database calls in a custom `BusinessTransaction` context manager.
- Extracted validation into a `@business_validation` decorator.

**After:**
```python
@staticmethod
@execution_timing
@audit_action("Manager Leave Approval")
@business_validation(validate_manager_approval)
def process_manager_approval(dto: LeaveApprovalDTO) -> Tuple[LeaveRequest, str]:
    with BusinessTransaction(f"Manager approval for leave {dto.leave_id}"):
        # ... core logic only
```

**Performance:**
Execution time is now systematically measured via the decorator without polluting business logic. Performance is identical or slightly improved as logic is cleanly isolated.

---

## 2. `process_hr_approval` (Leave Management)
**Before:**
Similar to manager approval, this function was tightly coupled with transaction management, generic error throwing, and raw argument lists.

**Problem:**
High duplication of boilerplate code (validations, transactions, error handling) seen in the manager approval function.

**Refactoring:**
- Applied the same advanced decorators and context managers.
- Utilized `LeaveApprovalDTO` and type hinting.

**After:**
```python
@staticmethod
@execution_timing
@audit_action("HR Leave Approval")
@business_validation(validate_hr_approval)
def process_hr_approval(dto: LeaveApprovalDTO) -> Tuple[LeaveRequest, str]:
    with BusinessTransaction(f"HR approval for leave {dto.leave_id}"):
        # ... core logic only
```

**Performance:**
Benefits from centralized transaction context management. Logging and monitoring hooks run completely orthogonally.

---

## 3. `monthly` (Attendance Summary View)
**Before:**
```python
counts = records.values('status').annotate(count=Count('status'))
breakdown = {choice[0]: 0 for choice in Attendance.STATUS_CHOICES}
for item in counts:
    breakdown[item['status']] = item['count']
    
data = {
    "employee_id": employee.id,
    "employee_name": f"{employee.first_name} {employee.last_name}",
    "month": month,
    "year": year,
    "total_days_logged": records.count(),
    "breakdown": breakdown
}
return Response({"success": True, "data": data})
```

**Problem:**
- Uses a basic `for` loop to build a dictionary from query results.
- Returns a raw, untyped dictionary, which makes it harder to maintain and prone to missing fields.

**Refactoring:**
- Replaced the loop with functional programming primitives: `map` and a `lambda` function.
- Encapsulated the return structure inside an `AttendanceSummaryDTO` dataclass.
- Used `asdict()` to convert the DTO to a response dictionary.

**After:**
```python
counts = records.values('status').annotate(count=Count('status'))
breakdown = {choice[0]: 0 for choice in Attendance.STATUS_CHOICES}

update_counts = dict(map(lambda item: (item['status'], item['count']), counts))
breakdown.update(update_counts)
    
dto = AttendanceSummaryDTO(
    employee_id=employee.id,
    employee_name=f"{employee.first_name} {employee.last_name}",
    month=month,
    year=year,
    total_days_logged=records.count(),
    breakdown=breakdown
)
return Response({"success": True, "data": asdict(dto)})
```

**Performance:**
`map` combined with a `lambda` is highly optimized in CPython, often outperforming manual Python-level `for` loops for dictionary comprehension generation.

---

## 4. `log_action` (Audit Logs Utils)
**Before:**
```python
def log_action(user, action, description, request=None):
    # Logs action strictly based on positional/named arguments.
```

**Problem:**
The function signature was rigid, preventing callers from easily passing additional metadata or varying context depending on the subsystem that invoked it.

**Refactoring:**
- Switched to using `*args` and `**kwargs`.
- Added logic to automatically collect and format unknown `kwargs` into an "Extra Context" appended to the description.
- Handled positional fallback correctly.

**After:**
```python
def log_action(*args, **kwargs):
    # Extracts known fields...
    extra_data = {k: v for k, v in kwargs.items() if k not in ['user', 'action', 'description', 'request']}
    if extra_data:
        description = f"{description} | Extra Context: {extra_data}"
    # ...
```

**Performance:**
Allows for zero-cost abstraction when additional arguments are not needed, while dramatically improving the utility of logging across the platform.

---

## 5. `custom_exception_handler` (API Exceptions)
**Before:**
Exceptions thrown across the app were unstructured, mostly relying on generic `ValueError` or standard DRF `ValidationError` strings.

**Problem:**
Clients had to parse exception strings to determine business logic failure reasons (e.g., "Leave request is not in a valid state...").

**Refactoring:**
- Created a class hierarchy starting with `HRMSBaseException`.
- Implemented specific errors: `EmployeeNotFoundError`, `InvalidWorkflowStateError`, etc.
- These enforce consistent string representations and HTTP-friendly error codes.

**After:**
```python
class InvalidWorkflowStateError(HRMSBaseException):
    def __init__(self, current_state, expected_state):
        super().__init__(f"Invalid state: {current_state}. Expected: {expected_state}.", "INVALID_WORKFLOW_STATE")
```

**Performance:**
No meaningful performance overhead, but massive improvements to application stability, testability, and clarity.
