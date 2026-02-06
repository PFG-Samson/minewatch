# MineWatch — Frequently Asked Questions (FAQ)

A central reference for users and developers covering system operation, troubleshooting, and scientific workflows.

---

## 🛠️ General & Setup

### Q: Why do I see a blank white screen on the Dashboard?
**A:** This usually happens if the map tries to calculate a view for a project that hasn't been configured yet. We have implemented fixes to handle these "empty states" gracefully, but ensure your backend is running to provide the necessary data.

### Q: Do I need to run both the frontend and backend?
**A:** **Yes.** MineWatch is a full-stack app. The **Frontend** (React) provides the interface, while the **Backend** (FastAPI) handles the database, satellite downloads, and scientific calculations. 
- Run Frontend: `npm run dev`
- Run Backend: `python -m backend.main`

### Q: Where did the "Mine Area Setup" go?
**A:** It has been moved from the dashboard sidebar to a dedicated **Settings** tab in the main navigation. This provides more space for configuration and a private preview map.

---

## 🛰️ Satellite Data (STAC)

### Q: Why does "Ingest via STAC" fail?
**A:** Common reasons include:
1. **No Project Boundary:** You must save a project boundary in the **Settings** tab first.
2. **Backend Offline:** If the Python server is down, search requests will fail.
3. **Cloud Cover:** If you set a low cloud cover limit (e.g., < 10%), the system may find zero usable scenes for your location.

### Q: How many bands are downloaded?
**A:** The system downloads **5 bands** per scene:
- **Red, Green, Blue:** For the true-color map.
- **NIR (Near-Infrared):** For vegetation health (NDVI).
- **SWIR (Short-Wave Infrared):** For soil/excavation detection (BSI).

### Q: How long does downloading take?
**A:** 
- **Ingestion (Metadata):** 1-3 seconds.
- **Syncing (Files):** ~2-5 minutes per scene depending on your connection. A typical "Change Analysis" compares two dates and takes **5-10 minutes**.

### Q: Where is the data stored?
**A:**
- **Database:** `backend/minewatch.db` (settings, alerts, scene logs).
- **Raw Tiff Files:** `backend/data/imagery/`.
- **Map Overlays:** `backend/data/cache/` (optimized PNGs).

---

## 🧪 Scientific Analysis

### Q: What is NDVI?
**A:** **Normalized Difference Vegetation Index.** It measures plant health. Values near 1.0 are lush greenery; values near 0 are dead or bare ground. A drop in NDVI is our primary way to detect illegal land clearing.

### Q: What is BSI?
**A:** **Bare Soil Index.** It highlights exposed earth, sand, and rock. An increase in BSI is the "smoking gun" for new mining excavations or road construction in a lease area.

### Q: What is NDWI?
**A:** **Normalized Difference Water Index.** It detects surface water. We use it to monitor the size of tailings ponds, flooded pits, or new water reservoirs.

### Q: How are alerts generated?
**A:** The app compares a **Baseline** scene with the **Latest** scene. If it finds a significant change (e.g., NDVI drop or BSI increase) over a specific area threshold (usually 0.5 hectares), it automatically creates a high-severity alert.

---

## 💻 Developer Notes

### Q: How do I update the database schema?
**A:** Schema changes are handled in `backend/main.py` within the `init_db()` function. For new columns (like the `description` field added recently), use the `ALTER TABLE` logic within the startup event to ensure existing databases are migrated.

### Q: How do I add a new scientific index?
**A:**
1. Add the formula to `backend/utils/spatial.py`.
2. Update `backend/analysis_pipeline.py` to include the required bands and call your new function.
3. Add a Toggle in the `LayerControl` within `Dashboard.tsx`.
