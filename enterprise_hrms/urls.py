from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def home_view(request):
    return JsonResponse(
        {
            "message": "HRMS API is running.",
            "available_endpoints": {
                "register": "/api/v1/auth/register/",
                "login": "/api/v1/auth/login/",
                "refresh": "/api/v1/auth/refresh/",
                "logout": "/api/v1/auth/logout/",
                "change_password": "/api/v1/auth/change-password/",
            },
        }
    )


urlpatterns = [
    path("", home_view, name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("enterprise_hrms.api.urls")),
]
