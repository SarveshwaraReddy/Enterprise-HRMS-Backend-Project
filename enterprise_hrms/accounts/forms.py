from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "phone", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data["phone"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user