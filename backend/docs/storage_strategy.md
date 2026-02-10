# Storage Strategy Documentation

## Current Implementation

### Storage Location
MineWatch uses **local disk storage** for satellite imagery data:
```
backend/data/imagery/
```

### Decision Rationale

**Chosen Approach:** Local Disk Storage

**Advantages:**
- ✅ Simple deployment (no cloud provider dependencies)
- ✅ No egress costs for large raster files
- ✅ Fast local access for analysis pipeline
- ✅ Suitable for single-site monitoring deployments
- ✅ Complete data sovereignty

**Acceptable For:**
- Single mine site monitoring (< 10GB total)
- Deployments with <100 scenes
- Organizations with on-premise requirements

**Limitations:**
- ⚠️ Not suitable for multi-site portfolios
- ⚠️ Requires backup strategy
- ⚠️ Limited by server disk capacity

---

## Directory Structure

```
backend/data/imagery/
├── {scene_uri}_B02.tif    # Blue band (10m resolution)
├── {scene_uri}_B03.tif    # Green band (10m resolution)
├── {scene_uri}_B04.tif    # Red band (10m resolution)
├── {scene_uri}_B08.tif    # NIR band (10m resolution)
└── {scene_uri}_B11.tif    # SWIR band (20m, resampled to 10m)
```

**Example:**
```
S2C_MSIL2A_20260204T093211_R136_T33PUP_20260204T130010_B02.tif
S2C_MSIL2A_20260204T093211_R136_T33PUP_20260204T130010_B03.tif
...
```

---

## File Naming Convention

**Pattern:** `{scene_uri}_{band}.tif`

Where:
- `scene_uri`: STAC item identifier from Microsoft Planetary Computer
- `band`: Sentinel-2 band identifier (B02, B03, B04, B08, B11)

**File Format:** GeoTIFF with embedded:
- CRS (usually UTM zone)
- Geotransform
- NoData values
- Compression (LZW or DEFLATE)

---

## Disk Space Requirements

### Per Scene
- **5 bands × ~100MB average** = ~500MB per scene
- Actual size varies by:
  - Scene coverage area
  - Cloud percentage
  - Compression ratio

### Typical Deployment
- **10 scenes** (1 year monthly): ~5GB
- **50 scenes** (multi-year): ~25GB
- **100 scenes** (full archive): ~50GB

### Recommendations
- Allocate minimum **20GB** for imagery storage
- Monitor with `df -h backend/data/imagery/`
- Implement cleanup policy (e.g., delete scenes >2 years old)

---

## Backup Strategy

### Option 1: Local Backup
```bash
# Daily backup to external drive
rsync -av backend/data/imagery/ /mnt/backup/minewatch-imagery/
```

### Option 2: Cloud Backup (Recommended)
```bash
# Sync to S3 for disaster recovery
aws s3 sync backend/data/imagery/ s3://minewatch-backup/imagery/
```

### Option 3: Database-Driven
Delete local files but keep metadata in `imagery_scene` table. Re-download from STAC when needed (slower but reduces storage).

---

## Cache Management

### RGB Preview Cache
Location: `backend/data/cache/`

Generated PNG previews (~2MB each) for web display:
```
preview_{scene_uri}.png
```

**Automatic Cleanup:**
- Cache expires after 7 days
- Regenerated on-demand via `/analysis-runs/{id}/imagery` endpoint

---

## Migration to Cloud Storage (P2)

### When to Migrate
Consider cloud storage when:
- Managing >5 mine sites
- Total imagery >100GB
- Need multi-region redundancy
- Require advanced lifecycle policies

### Target Architecture

**Option A: AWS S3**
```python
# In stac_downloader.py
s3_client.upload_file(
    local_path,
    bucket='minewatch-imagery',
    key=f'{site_id}/{scene_uri}/{band}.tif'
)
```

**Option B: Azure Blob Storage**
```python
blob_client.upload_blob(
    data=open(local_path, 'rb'),
    blob_type='BlockBlob'
)
```

### Migration Steps
1. Update `stac_downloader.py` to support storage backends
2. Create abstraction layer (`storage_backend.py`)
3. Implement `LocalStorageBackend` and `S3StorageBackend`
4. Update `analysis_pipeline.py` to stream from cloud
5. Migrate existing data with script

### Code Changes Required
```python
# storage_backend.py
class StorageBackend(ABC):
    @abstractmethod
    def save_band(self, scene_uri: str, band: str, data: bytes):
        pass
    
    @abstractmethod
    def get_band_path(self, scene_uri: str, band: str) -> str:
        pass

class LocalStorageBackend(StorageBackend):
    def save_band(self, scene_uri: str, band: str, data: bytes):
        path = Path("backend/data/imagery") / f"{scene_uri}_{band}.tif"
        path.write_bytes(data)
    
    def get_band_path(self, scene_uri: str, band: str) -> str:
        return str(Path("backend/data/imagery") / f"{scene_uri}_{band}.tif")
```

---

## Performance Considerations

### Read Performance
- **Local disk:** ~500 MB/s (SSD)
- **Network storage:** ~100 MB/s (1Gbps)
- **S3 (same region):** ~50-100 MB/s

### Analysis Impact
- Full 5-band analysis: ~2-3 seconds (local) vs ~10-15 seconds (cloud)
- For current scale, local storage provides best performance

---

## Security

### File Permissions
```bash
chmod 755 backend/data/imagery/
chmod 644 backend/data/imagery/*.tif
```

### Access Control
- Imagery files served only via authenticated API endpoints
- Direct file access blocked by web server configuration
- Static file mounting uses `/data/cache` only (not `/data/imagery`)

---

## Monitoring

### Disk Usage Alerts
```bash
# Add to cron: check if >80% full
USAGE=$(df backend/data/imagery | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $USAGE -gt 80 ]; then
    echo "Warning: Imagery storage >80% full"
fi
```

### Scene Count
```sql
SELECT COUNT(*) FROM imagery_scene;
SELECT COUNT(*) FROM imagery_scene WHERE created_at > datetime('now', '-30 days');
```

---

## Summary

✅ **Current:** Local disk storage at `backend/data/imagery/`  
✅ **Suitable for:** Single-site deployments (<100GB)  
✅ **Well-tested:** Proven with Sentinel-2 band downloads  
📋 **Future:** Cloud migration path documented for scale-up
