# API Reliability & Security Report

## 1. Global Exception Handling
- **Implementation**: Completely replaced the DRF exception handler in `enterprise_hrms/api/exceptions.py`.
- **Behavior**: All errors now return a strict enterprise JSON envelope:
  ```json
  {
      "success": false,
      "message": "Validation failed.",
      "error_code": "VALIDATION_FAILED",
      "details": { ... }
  }
  ```
- **Benefits**: Front-end consumers can now rely on `error_code` strings rather than parsing unpredictable HTTP 500 HTML traces.

## 2. API Abuse Prevention (Throttling)
- **Implementation**: Added `AnonRateThrottle` and `UserRateThrottle` to `REST_FRAMEWORK` settings.
- **Configuration**: Anonymous users are limited to 100 requests per day, and authenticated users to 1000 requests per day.
- **Benefits**: Protects the API from brute-forcing authentication endpoints, scraping sensitive data, and general Denial of Service (DoS) attacks.
