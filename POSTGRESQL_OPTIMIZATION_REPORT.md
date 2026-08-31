# PostgreSQL Optimization Report

## 1. Concurrency & Database Locks
- **Issue**: Two HR users could theoretically approve the same leave simultaneously, resulting in a race condition where both transactions succeed but the final state is corrupted.
- **Optimization**: Implemented `select_for_update()` inside a `transaction.atomic()` block in `LeaveService`. 
- **Effect**: If Transaction A begins an approval, Transaction B is forced to wait at the database level until A commits. This guarantees absolute data integrity.

## 2. Database Constraints
- **Optimization**: Added a `CheckConstraint` on `LeaveRequest` to enforce `end_date >= start_date`.
- **Effect**: It is now mathematically impossible for application code, bulk imports, or manual DBA queries to insert a leave request that ends before it begins.

## 3. Composite Indexes
- **Optimization**: Added a composite index `(employee, status)` to the `LeaveRequest` table.
- **Effect**: Speeds up the most common API query ("Show me all pending leave requests for this specific employee").
