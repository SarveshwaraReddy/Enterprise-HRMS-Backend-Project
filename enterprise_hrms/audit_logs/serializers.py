from rest_framework import serializers
from .models import AuditLog
from enterprise_hrms.accounts.models import User

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role']

class AuditLogSerializer(serializers.ModelSerializer):
    user_details = UserMinimalSerializer(source='user', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_details', 'action', 'description', 'ip_address', 'timestamp']
        read_only_fields = ['id', 'user', 'action', 'description', 'ip_address', 'timestamp']
