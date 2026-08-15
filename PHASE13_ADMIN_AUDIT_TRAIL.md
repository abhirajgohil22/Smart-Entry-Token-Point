# Phase 13: Admin Verification Portal & Audit Trail
## Completion Summary

### Overview
Phase 13 implements a comprehensive administrative portal for monitoring security photo events, campus gate activity, and enforcing privacy-compliant photo retention policies. The system provides admin staff with tools to inspect security events, manage verification overrides, and automatically clean up old data.

---

## Deliverables Completed

### 1. **Admin Dashboard Views for Security Photo Events**
**File:** [apps/security_photos/admin.py](apps/security_photos/admin.py)

**Features:**
- **List Display:** Request ID, User, Event Type, Captured Timestamp, Verification Status (color-coded), Face Recognition Status, IP Address, Face Confidence Score
- **Filtering:** By event type (REGISTRATION, LOGIN, TOKEN_GENERATION, TOKEN_REGENERATION), verification status (PENDING, VALIDATED, REJECTED), face recognition status, and date hierarchy
- **Search Capabilities:** User email/username, first/last name, request ID, nonce, IP address
- **Manual Override Actions:**
  - ✓ Mark as VALIDATED (approve rejected photos)
  - ✓ Mark as REJECTED (flag suspicious photos)
  - ✓ Toggle retention hold (extend to 90 days for investigation)
- **Field Protection:** Sensitive fields (id, user, image, timestamp, etc.) are read-only
- **Add/Delete Controls:** Prevents manual creation; delete restricted to superusers
- **Visual Enhancements:** 
  - Color-coded status badges (green=validated, red=rejected, yellow=pending)
  - Thumbnail image preview (200x200px)
  - Request ID links to full record view

**Admin Workflow:**
```
/admin/security_photos/securityphoto/ 
→ Filter by event type or status
→ View event details with image preview
→ Apply manual overrides if needed
→ Search by user, IP, or request ID
```

---

### 2. **Privacy Compliance Photo Retention Cleaner**
**File:** [apps/security_photos/management/commands/cleanup_old_photos.py](apps/security_photos/management/commands/cleanup_old_photos.py)

**Features:**
- **Automatic Data Purging:** Deletes security photos older than specified retention period (default: 30 days)
- **Admin Hold Preservation:** Respects `retention_until` field; flagged photos are never auto-deleted
- **Safe Preview Mode:** `--dry-run` flag shows what would be deleted without making changes
- **Configurable Retention:** `--days` parameter allows flexible policies
- **File Cleanup:** Deletes both database records and image files from storage
- **Comprehensive Logging:** Records deletion count, retention flags, and any errors

**Command Usage:**
```bash
# Dry-run preview (default 30 days)
python manage.py cleanup_old_photos --dry-run

# Execute cleanup (30-day retention)
python manage.py cleanup_old_photos

# Custom retention period (e.g., 60 days)
python manage.py cleanup_old_photos --days 60

# Dry-run with custom period
python manage.py cleanup_old_photos --days 14 --dry-run
```

**Privacy Compliance:**
- Implements GDPR data minimization principles
- Automatic purge eliminates unnecessary photo storage
- Admin retention holds allow investigation of suspicious events
- Audit logging tracks what was deleted and why

**Example Output:**
```
DRY RUN: Would delete 5 photo(s) older than 30 days.
  - req-001-abc (LOGIN) / student@example.com
  - req-002-def (TOKEN_GENERATION) / student@example.com
  ... and 3 more
```

---

### 3. **Admin Audit Trail Dashboard**
**File:** [templates/admin/audit_trail.html](templates/admin/audit_trail.html)

**Components:**

**A. Summary Cards:**
- Active Tokens Count (primary)
- Revoked Tokens Count (warning)
- Expired Tokens Count (danger)
- Total Events Count (info)

**B. Event Type Distribution:**
Shows breakdown of security events by category:
- Registration events
- Login events
- Token Generation events
- Token Regeneration events

**C. Verification Status Distribution:**
Shows breakdown by verification state:
- ✓ Validated (green)
- ✗ Rejected (red)
- ⏳ Pending (yellow)
- Processing (gray)

**D. Recent Security Photo Events Table:**
- Request ID (truncated with link)
- User email
- Event type badge
- Captured timestamp
- Verification status with color
- IP address
- Face confidence % (or N/A)

**E. Recent System Notifications Table:**
- User email
- Event type badge
- Channel (Email, System, or Both)
- Status (Sent, Failed, Queued)
- Email subject (truncated)
- Sent timestamp

**F. Admin Actions Section:**
Quick reference to:
- View full admin panel
- View all notifications
- Run cleanup commands

**Access:** `/api/security_photos/admin/audit-trail/` (staff-only)

---

### 4. **Notification Log Admin Interface**
**File:** [apps/notifications/admin.py](apps/notifications/admin.py)

**Features:**
- **List Display:** User email, Event type (colored badge), Channel (icon + label), Status (colored), Created date, Sent date
- **Filtering:** By event_type, channel, status, created/sent dates
- **Search:** User email, username, event type, subject
- **Field Protection:** Metadata, timestamps, error messages are read-only
- **Metadata Display:** Shows JSON metadata with biometric data scrubbed automatically
- **Actions:**
  - Mark as SENT (override for manual delivery)
  - Mark as FAILED (for retry queue)
- **Color-Coded Display:**
  - 🟢 Event type: Blue badge
  - 📧 Channel: Icon-based display (envelope, desktop, or both)
  - ✓ Status: Green=Sent, Red=Failed, Yellow=Queued

**Admin Workflow:**
```
/admin/notifications/notificationlog/
→ Filter by event type or channel
→ Search for specific user
→ View notification content and metadata
→ Apply delivery actions if needed
```

---

### 5. **Admin Dashboard View**
**File:** [apps/security_photos/views.py](apps/security_photos/views.py) - `AdminAuditTrailView`

**Features:**
- **Access Control:** Staff-only (requires `is_staff` permission)
- **Data Aggregation:** Collects:
  - Last 100 security photo events (selected_related for efficiency)
  - Active/revoked/expired token counts
  - Last 50 system notifications
  - Event type summary
  - Verification status summary
- **Context Data:**
  ```python
  {
      'recent_events': [...],        # Last 100 SecurityPhoto records
      'active_tokens': 42,
      'revoked_tokens': 8,
      'expired_tokens': 2,
      'recent_notifications': [...], # Last 50 NotificationLog records
      'event_summary': {             # Breakdown by event type
          'Registration': 150,
          'Login': 450,
          'Token Generation': 80,
          'Token Regeneration': 15,
      },
      'verification_summary': {      # Breakdown by verification status
          'Validated': 580,
          'Rejected': 5,
          'Pending': 12,
          'Processing': 8,
      }
  }
  ```

**URL Route:** `/api/security_photos/admin/audit-trail/`

---

### 6. **Base HTML Template**
**File:** [templates/base.html](templates/base.html)

- Responsive Bootstrap 5 layout
- FontAwesome 6 icon integration
- Navigation bar with admin links
- Message display for admin actions
- Consistent styling across admin pages
- Footer with contact info

---

## Test Coverage

**File:** [apps/security_photos/tests_admin.py](apps/security_photos/tests_admin.py)

**8 Comprehensive Tests Passed:**

1. ✓ **test_cleanup_deletes_old_photos** - Verifies deletion of photos older than retention period
2. ✓ **test_cleanup_preserves_retention_held_photos** - Confirms admin holds are respected
3. ✓ **test_cleanup_preserves_recent_photos** - Ensures recent photos are not deleted
4. ✓ **test_cleanup_dry_run_does_not_delete** - Validates --dry-run safety
5. ✓ **test_cleanup_with_custom_days** - Tests configurable retention periods
6. ✓ **test_security_photo_admin_read_only_fields** - Verifies field protection
7. ✓ **test_security_photo_admin_no_add_permission** - Confirms add prevention
8. ✓ **test_notification_log_admin_has_no_add_permission** - Confirms notification record protection

**Test Results:**
```
Ran 8 tests in 2.800s
OK ✓
```

---

## Privacy & Security Features

### Biometric Data Protection
- ✓ All face encodings, embeddings, raw images removed from notification logs
- ✓ Admin metadata display automatically scrubs sensitive fields
- ✓ Image previews only shown in staff-only admin panel
- ✓ IP addresses logged for security investigation (not for tracking)

### Access Control
- ✓ Admin dashboard requires staff permission
- ✓ Audit trail views restrict to authenticated staff
- ✓ Manual creation of security photos disabled
- ✓ Delete operations restricted to superusers

### Compliance
- ✓ GDPR data minimization: automatic purge of old photos
- ✓ Admin retention holds for investigation purposes
- ✓ Comprehensive audit trail of admin actions
- ✓ Django admin change logs track all modifications

---

## Integration Points

### With Existing Systems
- **SecurityPhoto Model:** Used for all REGISTRATION, LOGIN, TOKEN_GENERATION, TOKEN_REGENERATION events
- **NotificationLog Model:** Captures all security alerts without biometric data
- **CampusToken Model:** Provides token lifecycle status for dashboard summary
- **User Model:** Enables admin to search events by student email/username

### Workflow Integration
```
Registration/Login/Token Generation
  ↓
SecurityPhoto record created
  ↓
Verification & Face Recognition processed
  ↓
NotificationLog dispatched (scrubbed)
  ↓
Admin can view in audit trail
  ↓
After 30 days: cleanup_old_photos removes records
  ↓
(Unless admin extended retention for investigation)
```

---

## Deployment Instructions

### 1. Enable Admin Interface
Admin is automatically registered when Django loads. No additional configuration needed.

### 2. Schedule Photo Cleanup
Add to your deployment/cron job scheduler:

**Daily cleanup (30-day retention):**
```bash
0 2 * * * cd /path/to/project && .venv/bin/python manage.py cleanup_old_photos >> logs/cleanup.log 2>&1
```

**Weekly dry-run check (log only, no deletion):**
```bash
0 3 * * 0 cd /path/to/project && .venv/bin/python manage.py cleanup_old_photos --dry-run >> logs/cleanup_dryrun.log 2>&1
```

### 3. Monitor Logs
```bash
tail -f logs/cleanup.log
tail -f logs/cleanup_dryrun.log
```

---

## Admin Workflows

### Workflow 1: Monitor Recent Security Events
1. Login to `/admin/`
2. Click "Security Photos" in sidebar
3. Filter by event_type (e.g., "LOGIN")
4. Review verification_status and IP addresses
5. Click on suspicious events for full details

### Workflow 2: Override Photo Verification
1. Find photos with REJECTED status
2. Select multiple if needed
3. Choose action "Override: Mark as VALIDATED"
4. Click "Go" to apply
5. Confirmation message shows count updated

### Workflow 3: Flag Photos for Investigation
1. Find concerning photos
2. Select them
3. Click "Toggle retention hold (extend to 90 days)"
4. Photos will be preserved during regular cleanups

### Workflow 4: Run Data Cleanup
**Manual execution:**
```bash
python manage.py cleanup_old_photos --dry-run  # Preview first
python manage.py cleanup_old_photos             # Execute
```

**Check results:**
```bash
tail logs/cleanup.log
```

---

## System Requirements

- ✓ Django 4.2.4+
- ✓ Django admin framework (included)
- ✓ Pillow (for image preview)
- ✓ ReportLab (for PDF generation)
- ✓ Bootstrap 5 CDN (for UI)
- ✓ FontAwesome 6 CDN (for icons)

---

## Known Limitations & Future Enhancements

**Current:**
- Audit trail dashboard loads last 100 events (configurable via queryset)
- Cleanup is manual/cron-based (could use Celery for async)
- Image preview limited to admin panel (security by design)

**Future:**
- Real-time event streaming to dashboard
- Scheduled cleanup with Celery
- Advanced analytics (event heatmaps, verification failure rates)
- Automated alerts for suspicious verification patterns
- Export audit trail to PDF/CSV reports

---

## Verification Checklist

- [x] Admin interface displays security photos with filtering
- [x] Manual override controls work (VALIDATED/REJECTED)
- [x] Retention holds prevent deletion
- [x] Photo cleanup command respects retention policy
- [x] Dry-run mode doesn't delete photos
- [x] Notification logs display without biometric data
- [x] Admin dashboard loads event summary
- [x] All 8 tests pass
- [x] No blocking Django system check errors
- [x] Staff-only access enforced on admin views

---

## Files Modified/Created

```
✓ apps/security_photos/admin.py (CREATED)
✓ apps/security_photos/management/commands/cleanup_old_photos.py (CREATED)
✓ apps/security_photos/management/__init__.py (CREATED)
✓ apps/security_photos/management/commands/__init__.py (CREATED)
✓ apps/security_photos/views.py (MODIFIED - added AdminAuditTrailView)
✓ apps/security_photos/urls.py (MODIFIED - added audit trail route)
✓ apps/security_photos/tests_admin.py (CREATED)
✓ apps/notifications/admin.py (CREATED)
✓ templates/admin/audit_trail.html (CREATED)
✓ templates/base.html (CREATED)
```

---

**Phase 13 Status:** ✅ **COMPLETE**

All deliverables implemented, tested, and integrated. System is ready for production deployment with administrative oversight capabilities and privacy-compliant data retention.
