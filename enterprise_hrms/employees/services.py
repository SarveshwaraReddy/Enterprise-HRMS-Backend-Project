from enterprise_hrms.audit_logs.utils import log_action

class EmployeeService:
    @staticmethod
    def create_employee(serializer, request):
        emp = serializer.save()
        log_action(
            user=request.user,
            action="Employee Created",
            description=f"Registered employee: {emp.first_name} {emp.last_name} ({emp.employee_id})",
            request=request
        )
        return emp

    @staticmethod
    def update_employee(serializer, request):
        emp = serializer.save()
        log_action(
            user=request.user,
            action="Employee Updated",
            description=f"Updated employee: {emp.first_name} {emp.last_name} ({emp.employee_id})",
            request=request
        )
        return emp

    @staticmethod
    def delete_employee(instance, request):
        emp_name = f"{instance.first_name} {instance.last_name}"
        emp_id = instance.employee_id
        instance.delete()
        log_action(
            user=request.user,
            action="Employee Deleted",
            description=f"Deleted employee: {emp_name} ({emp_id})",
            request=request
        )
