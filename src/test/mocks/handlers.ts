import { http, HttpResponse } from "msw";

const API_ROOT = "http://localhost:8000";

export const handlers = [
    http.get(`${API_ROOT}/health*`, () => HttpResponse.json({ status: "ok" })),

    http.get(`${API_ROOT}/mine-area*`, () => HttpResponse.json({
        name: "Mock Mine",
        description: "Mock Mine Description",
        boundary: { type: "Polygon", coordinates: [[[10, 10], [11, 10], [11, 11], [10, 10]]] },
        buffer_km: 2.0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        area_ha: 100.0
    })),

    http.get(`${API_ROOT}/analysis-runs/trends`, () => HttpResponse.json([])),

    http.get(`${API_ROOT}/analysis-runs/latest/stats`, () => HttpResponse.json({
        has_data: true,
        vegetation_loss_ha: 10.5,
        vegetation_gain_ha: 2.1,
        mining_expansion_ha: 5.4,
        water_accumulation_ha: 1.2,
        total_change_ha: 19.2,
        last_updated: new Date().toISOString()
    })),

    http.get(`${API_ROOT}/analysis-runs/:runId/imagery`, () => HttpResponse.json({
        baseline: { url: "/mock-baseline.png", bounds: [10, 10, 11, 11] },
        latest: { url: "/mock-latest.png", bounds: [10, 10, 11, 11] }
    })),

    http.get(`${API_ROOT}/analysis-runs/:runId`, ({ params }) => HttpResponse.json({
        run: {
            id: Number(params.runId), baseline_date: "2024-01-01", latest_date: "2024-02-01",
            status: "completed", created_at: new Date().toISOString()
        },
        zones: { type: "FeatureCollection", features: [] }
    })),

    http.get(`${API_ROOT}/analysis-runs`, () => HttpResponse.json([
        {
            id: 1, baseline_date: "2024-01-01", latest_date: "2024-02-01",
            status: "completed", created_at: new Date().toISOString(),
            mean_ndvi: 0.5, mean_ndwi: 0.2, mean_bsi: 0.1
        }
    ])),

    http.get(`${API_ROOT}/alerts*`, () => HttpResponse.json([
        {
            id: 1, run_id: 1, type: "vegetation_loss", title: "Significant Vegetation Loss",
            description: "Large area of vegetation loss detected.", location: "North sector",
            severity: "high", created_at: new Date().toISOString()
        }
    ])),

    http.get(`${API_ROOT}/imagery/latest/preview`, () => HttpResponse.json({
        preview: { url: "/mock-preview.png", bounds: [10, 10, 11, 11] },
        message: "Latest imagery preview"
    })),

    http.get(`${API_ROOT}/imagery/latest`, () => HttpResponse.json({
        id: 2, source: "Sentinel-2", acquired_at: "2024-02-01",
        cloud_cover: 5.0, uri: "S2A_MSIL2A_TEST"
    })),

    http.get(`${API_ROOT}/imagery`, () => HttpResponse.json([
        { id: 1, source: "Sentinel-2", acquired_at: "2024-01-01", cloud_cover: 10.0, uri: "S2A_MSIL2A_BASE" },
        { id: 2, source: "Sentinel-2", acquired_at: "2024-02-01", cloud_cover: 5.0, uri: "S2A_MSIL2A_LATEST" }
    ])),

    http.post(`${API_ROOT}/analysis-runs*`, () => HttpResponse.json({
        id: 1, baseline_date: "2024-01-01", latest_date: "2024-02-01",
        status: "completed", created_at: new Date().toISOString()
    })),

    http.post(`${API_ROOT}/jobs/ingest-stac*`, () => HttpResponse.json([])),

    http.get(`${API_ROOT}/alert-rules*`, () => HttpResponse.json({ rules: {} })),
];
