# Phase 14: Analytics & Reporting Tools
## Completion Summary

### Overview
Phase 14 implements comprehensive analytics and reporting capabilities for monitoring system performance, token issuance metrics, biometric validation statistics, and system health. Security officers and administrators can generate detailed reports in Excel and PDF formats for auditing, compliance, and operational insights.

---

## Deliverables Completed

### 1. **Token Analytics Service**
**File:** [apps/tokens/analytics.py](apps/tokens/analytics.py) - `TokenAnalyticsService` class

**Features:**
- **Daily Token Volume:** Aggregates token counts by status (ACTIVE, REVOKED, EXPIRED) for each day
- **Weekly Token Volume:** Summarizes weekly token generation trends
- **Token Status Summary:** Provides current distribution of all tokens by status
- **Date Range Queries:** Configurable start/end dates or trailing day period (default: last 30 days)

**Methods:**

```python
# Daily token volume for date range
daily_data = TokenAnalyticsService.get_daily_token_volume(
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 15)
)
# Returns: [
#   {'date': '2026-08-01', 'total': 42, 'ACTIVE': 38, 'REVOKED': 3, 'EXPIRED': 1},
#   {'date': '2026-08-02', 'total': 45, 'ACTIVE': 41, 'REVOKED': 2, 'EXPIRED': 2},
#   ...
# ]

# Weekly token volume
weekly_data = TokenAnalyticsService.get_weekly_token_volume(
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31)
)
# Returns: [
#   {'week': 'Week 1 (2026-08-01 to 2026-08-07)', 'total': 298, 'ACTIVE': 270, ...},
#   ...
# ]

# Overall token status distribution
status_summary = TokenAnalyticsService.get_token_status_summary()
# Returns: [
#   {'status': 'ACTIVE', 'count': 1250},
#   {'status': 'REVOKED', 'count': 45},
#   {'status': 'EXPIRED', 'count': 320}
# ]
```

**Use Cases:**
- Monitor daily token generation rates
- Track token lifecycle and expiration patterns
- Identify revocation trends (security incidents)
- Capacity planning and load forecasting

---

### 2. **Photo Validation Analytics Service**
**File:** [apps/tokens/analytics.py](apps/tokens/analytics.py) - `PhotoValidationAnalyticsService` class

**Features:**
- **Validation Success Rates:** Percentage of photos successfully validated vs. rejected
- **Event Type Breakdown:** Metrics segregated by event type (REGISTRATION, LOGIN, TOKEN_GENERATION, TOKEN_REGENERATION)
- **Daily Validation Metrics:** Track validation trends by date and verification status
- **Comprehensive Stats:** VALIDATED, REJECTED, PENDING, PROCESSING counts and rates

**Methods:**

```python
# Overall validation success rate
validation_stats = PhotoValidationAnalyticsService.get_validation_success_rate(
    event_type='LOGIN',  # Optional filter
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 15)
)
# Returns: {
#   'validated': 450,
#   'rejected': 12,
#   'pending': 3,
#   'processing': 1,
#   'total': 466,
#   'success_rate': 96.57
# }

# Breakdown by event type
by_event_type = PhotoValidationAnalyticsService.get_validation_by_event_type(
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 15)
)
# Returns: [
#   {'event_type': 'LOGIN', 'validated': 450, 'rejected': 12, 'pending': 3, 'success_rate': 96.57},
#   {'event_type': 'REGISTRATION', 'validated': 120, 'rejected': 5, 'pending': 1, 'success_rate': 95.97},
#   ...
# ]

# Daily validation metrics
daily_metrics = PhotoValidationAnalyticsService.get_daily_validation_metrics()
# Returns: [
#   {'date': '2026-08-01', 'VALIDATED': 125, 'REJECTED': 3, 'PENDING': 2, 'PROCESSING': 0},
#   {'date': '2026-08-02', 'VALIDATED': 132, 'REJECTED': 4, 'PENDING': 1, 'PROCESSING': 1},
#   ...
# ]
```

**Use Cases:**
- Quality assurance for face recognition accuracy
- Identify problem areas (e.g., high rejection rates on a specific day)
- Biometric system calibration decisions
- Compliance reporting for photo validation audits

---

### 3. **Biometric Subsystem Analytics Service**
**File:** [apps/tokens/analytics.py](apps/tokens/analytics.py) - `BiometricSubsystemAnalyticsService` class

**Features:**
- **Face Recognition Status:** Reports whether face recognition is enabled and performance data
- **Success vs. Failure Rates:** Tracks face recognition success, failures, unavailability, and not-run counts
- **Confidence Score Statistics:** Average, minimum, and maximum confidence scores with sample size
- **Comprehensive System Health:** Integrated view of biometric subsystem operation

**Methods:**

```python
# Face recognition feature status
fr_status = BiometricSubsystemAnalyticsService.get_face_recognition_status()
# Returns: {
#   'face_recognition_enabled': True,
#   'liveness_enabled': True,
#   'status': 'OPERATIONAL' or 'DEGRADED' or 'DISABLED'
# }

# Face recognition performance metrics
performance = BiometricSubsystemAnalyticsService.get_face_recognition_performance()
# Returns: {
#   'success': 850,
#   'failed': 25,
#   'unavailable': 8,
#   'not_run': 5,
#   'total': 888,
#   'success_rate': 95.72
# }

# Confidence score statistics
confidence = BiometricSubsystemAnalyticsService.get_average_confidence_score()
# Returns: {
#   'average_confidence': 0.876,
#   'min_confidence': 0.421,
#   'max_confidence': 0.998,
#   'sample_size': 850
# }
```

**Use Cases:**
- Monitor biometric subsystem health and reliability
- Identify confidence score thresholds (e.g., "photos below 0.7 have high rejection rate")
- Capacity planning for biometric processing
- Compliance with biometric accuracy requirements

---

### 4. **System Health Analytics Service**
**File:** [apps/tokens/analytics.py](apps/tokens/analytics.py) - `SystemHealthAnalyticsService` class

**Features:**
- **Aggregated Metrics:** Combines token, validation, and biometric metrics into single view
- **Operational Status:** Overall system health assessment
- **Drill-Down Capabilities:** Links to detailed analytics for investigation

**Methods:**

```python
# Comprehensive system health summary
health = SystemHealthAnalyticsService.get_system_health_summary()
# Returns: {
#   'tokens': {
#     'total': 1615,
#     'ACTIVE': 1250,
#     'REVOKED': 45,
#     'EXPIRED': 320
#   },
#   'validation': {
#     'validated': 450,
#     'rejected': 12,
#     'pending': 3,
#     'processing': 1,
#     'total': 466,
#     'success_rate': 96.57
#   },
#   'biometric': {
#     'face_recognition_enabled': True,
#     'liveness_enabled': True,
#     'status': 'OPERATIONAL'
#   },
#   'biometric_status': {
#     'success': 850,
#     'failed': 25,
#     'unavailable': 8,
#     'not_run': 5,
#     'total': 888,
#     'success_rate': 95.72
#   }
# }
```

**Use Cases:**
- Executive dashboards summarizing system performance
- Alert thresholds on key metrics (e.g., "if validation success rate < 90%, trigger alert")
- Incident investigation starting point

---

### 5. **Excel Report Generator**
**File:** [apps/tokens/exports.py](apps/tokens/exports.py) - `ExcelReportGenerator` class

**Features:**
- **Multi-Sheet Layout:** 
  - **Sheet 1: Token Volume** - Daily and weekly token trends
  - **Sheet 2: Photo Validation** - Overall validation metrics and event-type breakdown
  - **Sheet 3: Biometric Status** - Face recognition performance and confidence scores
- **Professional Formatting:** 
  - Styled headers with navy blue background (#1F4788) and white text
  - Bordered cells with appropriate number/percentage formatting
  - Column width auto-adjustment for readability
- **Date Range Export:** Configurable start/end dates or trailing day period

**Output Format:**
- File Extension: `.xlsx`
- MIME Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Compatibility: Microsoft Excel, Google Sheets, LibreOffice Calc

**Methods:**

```python
from apps.tokens.exports import ExcelReportGenerator
from datetime import datetime, timedelta

# Create Excel report for 14-day period
generator = ExcelReportGenerator()
bytes_io = generator.generate_full_report(
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 15)
)

# Write to file
with open('analytics_report.xlsx', 'wb') as f:
    f.write(bytes_io.getvalue())
```

**Use Cases:**
- Executive reports for stakeholder briefings
- Data archival and compliance records
- Integration with BI tools and data warehouses
- Email delivery of periodic reports

---

### 6. **PDF Report Generator**
**File:** [apps/tokens/exports.py](apps/tokens/exports.py) - `PDFReportGenerator` class

**Features:**
- **Multi-Page Layout:** Each section on new page for clarity
- **Professional Tables:** ReportLab-based rendering with proper alignment
- **Dynamic Content:** Adapts to date range and available data
- **Print-Ready Format:** Optimized for printing and archival

**Output Format:**
- File Extension: `.pdf`
- MIME Type: `application/pdf`
- Pages: 3-5 pages depending on data volume
- Font: Helvetica (Helvetica-Bold for headers)

**Methods:**

```python
from apps.tokens.exports import PDFReportGenerator
from datetime import datetime

# Create PDF report
generator = PDFReportGenerator()
bytes_io = generator.generate_full_report(
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 15)
)

# Write to file
with open('analytics_report.pdf', 'wb') as f:
    f.write(bytes_io.getvalue())
```

**Use Cases:**
- Official audit reports (immutable format)
- Compliance documentation (FERPA, security standards)
- Regulatory submissions
- Email delivery (universal compatibility)

---

### 7. **Analytics REST API Endpoints**
**File:** [apps/tokens/views_analytics.py](apps/tokens/views_analytics.py)

**Routes:**

#### A. Token Analytics Endpoint
```http
GET /api/v1/tokens/analytics/tokens/
Authorization: Bearer <JWT_TOKEN>
Query Parameters: start_date, end_date, days (optional)

Response: 200 OK
{
  "daily_volume": [...],
  "weekly_volume": [...],
  "status_summary": [...]
}
```

#### B. Photo Validation Analytics Endpoint
```http
GET /api/v1/tokens/analytics/photos/
Authorization: Bearer <JWT_TOKEN>
Query Parameters: start_date, end_date, days (optional)

Response: 200 OK
{
  "overall": {
    "validated": 450,
    "rejected": 12,
    "success_rate": 96.57,
    ...
  },
  "by_event_type": [...],
  "daily_metrics": [...]
}
```

#### C. Biometric Analytics Endpoint
```http
GET /api/v1/tokens/analytics/biometric/
Authorization: Bearer <JWT_TOKEN>

Response: 200 OK
{
  "status": {
    "face_recognition_enabled": true,
    "liveness_enabled": true,
    "status": "OPERATIONAL"
  },
  "performance": {...},
  "confidence_scores": {...}
}
```

#### D. System Health Endpoint
```http
GET /api/v1/tokens/analytics/health/
Authorization: Bearer <JWT_TOKEN>

Response: 200 OK
{
  "tokens": {...},
  "validation": {...},
  "biometric": {...},
  "biometric_status": {...}
}
```

#### E. Excel Report Export Endpoint
```http
GET /api/v1/tokens/reports/excel/?start_date=2026-08-01&end_date=2026-08-15
Authorization: Bearer <JWT_TOKEN>

Response: 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="analytics_report.xlsx"
[Binary XLSX data]
```

#### F. PDF Report Export Endpoint
```http
GET /api/v1/tokens/reports/pdf/?start_date=2026-08-01&end_date=2026-08-15
Authorization: Bearer <JWT_TOKEN>

Response: 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="analytics_report.pdf"
[Binary PDF data]
```

**Common Query Parameters:**
- `start_date` (YYYY-MM-DD): Report start date (optional)
- `end_date` (YYYY-MM-DD): Report end date (optional)
- `days` (integer): Trailing day period if dates not specified (default: 30)

**Error Responses:**
```http
400 Bad Request
{
  "error": "Invalid date format. Use ISO format (YYYY-MM-DD)"
}

401 Unauthorized
{
  "detail": "Authentication credentials were not provided."
}

500 Internal Server Error
{
  "error": "Report generation failed"
}
```

**Authentication:**
- Requires valid JWT token in `Authorization: Bearer <token>` header
- Provided by authentication system (Phase 1-4)

---

## Testing & Verification

### Test Coverage
**File:** [apps/tokens/tests_analytics.py](apps/tokens/tests_analytics.py)

**Test Suites:**
1. **TokenAnalyticsServiceTests** (3 tests)
   - ✓ Daily token volume calculation
   - ✓ Weekly token volume calculation
   - ✓ Token status summary

2. **PhotoValidationAnalyticsServiceTests** (3 tests)
   - ✓ Validation success rate calculation
   - ✓ Validation breakdown by event type
   - ✓ Daily validation metrics

3. **BiometricAnalyticsServiceTests** (3 tests)
   - ✓ Face recognition status
   - ✓ Face recognition performance metrics
   - ✓ Average confidence score statistics

4. **SystemHealthAnalyticsServiceTests** (1 test)
   - ✓ System health summary aggregation

5. **ExcelReportGeneratorTests** (1 test)
   - ✓ Excel report generation with 3 sheets

6. **PDFReportGeneratorTests** (1 test)
   - ✓ PDF report generation and format validation

7. **AnalyticsAPIViewTests** (6 tests)
   - ✓ Token analytics endpoint
   - ✓ Photo validation endpoint
   - ✓ Biometric analytics endpoint
   - ✓ System health endpoint
   - ✓ Excel report export endpoint
   - ✓ PDF report export endpoint
   - ✓ Invalid date range error handling

**Test Results:**
```
Ran 19 tests in 4.459s
OK
```

### All Tests Passing
- Phase 13 Tests: 8/8 ✓
- Phase 14 Tests: 19/19 ✓
- **Total: 27/27 ✓**

---

## Usage Examples

### 1. Programmatic Analytics Query
```python
from apps.tokens.analytics import TokenAnalyticsService
from datetime import datetime, timedelta

# Get last 7 days of token activity
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

daily_volume = TokenAnalyticsService.get_daily_token_volume(start_date, end_date)

for day_data in daily_volume:
    print(f"{day_data['date']}: {day_data['total']} tokens "
          f"({day_data['ACTIVE']} active, "
          f"{day_data['REVOKED']} revoked)")
```

### 2. Curl API Request
```bash
# Get token analytics
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/tokens/analytics/tokens/?days=7"

# Download Excel report
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/tokens/reports/excel/?start_date=2026-08-01&end_date=2026-08-15" \
  -o report.xlsx

# Download PDF report
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/tokens/reports/pdf/" \
  -o report.pdf
```

### 3. Scheduled Report Generation
```bash
# Cron job for weekly report (every Sunday at 8 AM)
0 8 * * 0 curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/tokens/reports/excel/?days=7" \
  -o /reports/weekly_$(date +\%Y\%m\%d).xlsx
```

---

## Deployment Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Includes: openpyxl 3.1.2, pandas 2.1.1, reportlab 5.0.0
```

### 2. Database Migrations
```bash
python manage.py migrate
```

### 3. Collect Static Files (Production)
```bash
python manage.py collectstatic --noinput
```

### 4. Run Tests
```bash
python manage.py test apps.tokens.tests_analytics -v 2
```

### 5. Start Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

### 6. Production Deployment (with Gunicorn)
```bash
gunicorn project.wsgi:application --bind 0.0.0.0:8000
```

---

## Security & Compliance Considerations

### 1. Authentication
- All analytics endpoints require valid JWT token
- Prevents unauthorized access to system metrics
- Implements consistent auth layer from Phase 1-4

### 2. Data Privacy
- Analytics do NOT include sensitive user data (PII)
- Only aggregated metrics and counts are exposed
- Photos and biometric data remain private

### 3. Rate Limiting
- Integrate with Phase 10 throttling for API endpoints
- Prevents abuse of report generation (resource-intensive)

### 4. Audit Logging
- All report generation logged to NotificationLog
- Tracks who accessed which reports when
- Supports compliance audits

### 5. Export Compliance
- PDF reports use immutable format for regulatory archival
- Excel exports support audit data preservation
- Both formats include date range metadata

---

## Performance Optimization

### 1. Database Query Optimization
- Analytics services use Django ORM aggregation (not Python loops)
- `Count()`, `Q()` filters minimize database load
- Date-based indexing on created_at fields

### 2. Report Generation Caching
- Large reports can be cached in Redis for 1 hour
- Prevents repeated expensive computations
- User requests trigger regeneration if data changed

### 3. Pagination Recommendations
- For large date ranges, consider paginating daily volume results
- API responses limited to last 30 days by default

---

## Future Enhancements (Optional)

1. **Real-Time Dashboards:** WebSocket updates for live metric streaming
2. **Custom Report Builder:** Allow admins to select metrics and export format
3. **Scheduled Reports:** Automatic email delivery of weekly/monthly reports
4. **Data Visualization:** Charts and graphs in web dashboard
5. **Advanced Filtering:** Geographic, device, or user-cohort analytics
6. **Anomaly Detection:** Alerts on unusual metric patterns

---

## Files Summary

| File | Purpose | Lines |
|------|---------|-------|
| `apps/tokens/analytics.py` | Analytics services (4 classes) | 260+ |
| `apps/tokens/exports.py` | Excel and PDF generators | 450+ |
| `apps/tokens/views_analytics.py` | REST API endpoints | 180+ |
| `apps/tokens/urls.py` (modified) | Analytics routes | 6 new routes |
| `apps/tokens/tests_analytics.py` | Comprehensive test suite | 400+ |
| `requirements.txt` (modified) | Dependencies | +2 packages |

---

## Summary

Phase 14 successfully implements a complete analytics and reporting infrastructure for the Smart Campus Token Management System. The solution provides:

- **4 Analytics Services** aggregating token, photo validation, biometric, and system health metrics
- **2 Export Generators** producing professional Excel and PDF reports
- **6 REST API Endpoints** for programmatic access to analytics data
- **19 Comprehensive Tests** validating all functionality
- **100% Test Pass Rate** with proper error handling and edge cases

The system enables administrators and security officers to make data-driven decisions about system performance, identify trends, and maintain compliance with regulatory requirements.

**Status: ✓ COMPLETE AND TESTED**
