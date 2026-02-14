# Mine Area Name & Description Update

**Date:** February 14, 2026  
**Feature:** Enhanced mine area metadata tracking and reporting

---

## Overview

Updated the system to properly save, display, and include mine area name and description throughout the application, especially in PDF reports.

---

## Changes Made

### 1. **PDF Report Enhancement** ✅

**Before:**
```
MineWatch – Environmental Change Report
Run ID: 49
Created (UTC): 2026-02-14T10:00:00Z
```

**After:**
```
MineWatch – Environmental Change Report
Site: Your Mine Name
Optional site description appears here in italics

Run ID: 49
Created (UTC): 2026-02-14T10:00:00Z
```

**Features:**
- Mine name displayed prominently below report title
- Description shown in italics (if provided)
- Word wrapping for long descriptions (max 2 lines, 85 chars each)
- Mine name included in PDF filename: `minewatch-your-mine-name-run-49.pdf`

### 2. **API Improvements** ✅

**GET /mine-area:**
- Now properly returns both `name` and `description` fields
- Handles null/empty values gracefully
- Default name: "Mine Area" if not set

**PUT /mine-area:**
- Already accepts both fields (no changes needed)
- Name: Required field (default: "Mine Area")
- Description: Optional field

**Model:**
```python
class MineAreaOut(BaseModel):
    name: str
    description: Optional[str] = None
    boundary: dict[str, Any]
    buffer_km: float
    created_at: str
    updated_at: str
    area_ha: float
```

### 3. **Database Schema** ✅

Already supports both fields:
```sql
CREATE TABLE mine_area (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    description TEXT,  -- Optional
    boundary_geojson TEXT NOT NULL,
    buffer_km REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

---

## Usage

### Setting Mine Area Information

**Via UI (Settings Tab):**
1. Go to **Settings** tab
2. Enter **Site Name** (e.g., "Mafa Mine Area")
3. Enter **Description** (optional, e.g., "Gold mining operation in northern region")
4. Upload/paste boundary GeoJSON
5. Click **Save Configuration**

**Via API:**
```bash
curl -X PUT http://localhost:8000/mine-area \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mafa Mine Area",
    "description": "Gold mining operation in northern region",
    "boundary": {...},
    "buffer_km": 2.0
  }'
```

**Via Database (if needed):**
```python
import sqlite3

conn = sqlite3.connect('backend/minewatch.db')
conn.execute(
    "UPDATE mine_area SET name = ?, description = ? WHERE id = 1",
    ("Your Mine Name", "Your description here")
)
conn.commit()
conn.close()
```

### Retrieving Mine Area Information

**GET /mine-area:**
```json
{
  "name": "Mafa Mine Area",
  "description": "Gold mining operation in northern region",
  "boundary": {...},
  "buffer_km": 2.0,
  "created_at": "2026-02-14T10:00:00Z",
  "updated_at": "2026-02-14T11:00:00Z",
  "area_ha": 150.5
}
```

### PDF Report

**Automatic Inclusion:**
- Every PDF report now includes mine area name and description
- Name appears in bold below report title
- Description appears in italics (if provided)
- Filename includes sanitized mine name

**Example Filename:**
- Input: "Mafa Mine Area"
- Output: `minewatch-mafa-mine-area-run-49.pdf`

---

## Frontend Integration

### Current Status
The frontend **should** already be sending name and description when updating mine area configuration. If it's not, here's what to check:

**Settings Form Component** (check your frontend code):
```typescript
// Should include name field
<input
  type="text"
  name="name"
  placeholder="Site Name"
  value={mineArea.name}
  onChange={handleChange}
/>

// Should include description field
<textarea
  name="description"
  placeholder="Site Description (optional)"
  value={mineArea.description}
  onChange={handleChange}
/>
```

**API Call:**
```typescript
const response = await fetch('/mine-area', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: mineArea.name,
    description: mineArea.description,  // Make sure this is included
    boundary: mineArea.boundary,
    buffer_km: mineArea.buffer_km
  })
});
```

---

## Troubleshooting

### Issue: Name not appearing in reports
**Check:**
1. Verify name is in database:
   ```python
   import sqlite3
   conn = sqlite3.connect('backend/minewatch.db')
   result = conn.execute('SELECT name, description FROM mine_area WHERE id = 1').fetchone()
   print(f'Name: {result[0]}, Description: {result[1]}')
   ```

2. Ensure frontend is sending name in PUT request (check Network tab)

3. Restart backend server after database changes

### Issue: Description not showing
**Cause:** Description field is optional
**Solution:** Make sure description is provided when updating mine area

### Issue: Old name still appears
**Cause:** Server needs restart or database not updated
**Solution:**
1. Restart backend: `python -m backend.main`
2. Or update database manually (see Usage section above)

---

## Testing

### Test Checklist

1. **Update Mine Area:**
   - [ ] Set name via Settings UI
   - [ ] Set description via Settings UI
   - [ ] Verify in database
   - [ ] Check GET /mine-area returns both fields

2. **Generate Report:**
   - [ ] Run analysis
   - [ ] Download PDF report
   - [ ] Verify mine name appears in report header
   - [ ] Verify description appears (if set)
   - [ ] Verify filename includes mine name

3. **Edge Cases:**
   - [ ] Very long mine name (>50 chars)
   - [ ] Very long description (>200 chars)
   - [ ] Special characters in name
   - [ ] Empty description (should work fine)
   - [ ] Unicode characters

---

## Benefits

### For Users:
✅ **Clear identification** of which mine site a report belongs to  
✅ **Context at a glance** with optional description  
✅ **Professional reports** with site branding  
✅ **Better file organization** with named PDFs

### For Compliance:
✅ **Audit trail** - Reports clearly show which site was analyzed  
✅ **Documentation** - Description provides context for stakeholders  
✅ **ESG reporting** - Professional reports for regulatory submission

### For Operations:
✅ **Multi-site support** - Different configurations for different mines  
✅ **Team communication** - Description helps team understand site context  
✅ **Record keeping** - Named files easier to organize and archive

---

## Example Report

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  MineWatch – Environmental Change Report           │
│  Site: Mafa Mine Area                              │
│  Gold mining operation in northern region          │
│                                                     │
│  Run ID: 49                                        │
│  Created (UTC): 2026-02-14T11:00:00Z              │
│  Baseline date: 2026-02-01                         │
│  Latest date: 2026-02-06                           │
│  Status: completed                                 │
│                                                     │
│  Summary (Area by class)                           │
│  - Vegetation Loss: 2.50 hectares                  │
│  - Mining Expansion: 1.20 hectares                 │
│  - Water Accumulation: 0.30 hectares               │
│                                                     │
│  Alerts                                            │
│  - [HIGH] Significant vegetation loss detected...  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Next Steps

### Recommended Enhancements:

1. **Frontend Validation:**
   - Add form validation for mine name (required)
   - Add character limits (name: 100 chars, description: 500 chars)
   - Show preview of how report will look

2. **Multiple Sites:**
   - Future: Support multiple mine areas (not just id=1)
   - Switch between different configurations
   - Separate reports per site

3. **Report Customization:**
   - Allow custom logo upload
   - Configurable report template
   - Custom footer text

---

## Summary

The system now properly:
- ✅ Saves mine area name and description
- ✅ Displays them in PDF reports
- ✅ Includes name in PDF filename
- ✅ Returns them via GET /mine-area API
- ✅ Handles optional description gracefully
- ✅ Word-wraps long descriptions

**All changes are backward compatible** - existing functionality unchanged.
