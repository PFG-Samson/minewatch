export const API_BASE_URL = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export type AlertDto = {
  id: number;
  run_id: number | null;
  type: "vegetation_loss" | "boundary_breach" | "threshold_exceeded" | string;
  title: string;
  description: string;
  location: string;
  severity: "high" | "medium" | "low" | string;
  created_at: string;
};

export type AnalysisRunCreateDto = {
  baseline_date?: string;
  latest_date?: string;
};

export type AnalysisRunDto = {
  id: number;
  baseline_date: string | null;
  latest_date: string | null;
  status: string;
  created_at: string;
};

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    id?: number | string;
    properties?: Record<string, unknown>;
    geometry: {
      type: string;
      coordinates: unknown;
    };
  }>;
};

export type AnalysisRunWithZonesDto = {
  run: AnalysisRunDto;
  zones: GeoJsonFeatureCollection;
};

export type MineAreaUpsertDto = {
  name: string;
  boundary: Record<string, unknown>;
  buffer_km: number;
};

export type MineAreaDto = {
  name: string;
  boundary: Record<string, unknown>;
  buffer_km: number;
  created_at: string;
  updated_at: string;
};

export type ImagerySceneDto = {
  id: number;
  source: string;
  acquired_at: string;
  cloud_cover: number | null;
  footprint: Record<string, unknown> | null;
  uri: string | null;
  created_at: string;
};

export async function listAlerts(limit = 50): Promise<AlertDto[]> {
  return request<AlertDto[]>(`/alerts?limit=${encodeURIComponent(String(limit))}`);
}

export async function createAnalysisRun(payload: AnalysisRunCreateDto = {}): Promise<AnalysisRunDto> {
  return request<AnalysisRunDto>("/analysis-runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAnalysisRun(runId: number): Promise<AnalysisRunWithZonesDto> {
  return request<AnalysisRunWithZonesDto>(`/analysis-runs/${encodeURIComponent(String(runId))}`);
}

export async function getMineArea(): Promise<MineAreaDto> {
  return request<MineAreaDto>("/mine-area");
}

export async function upsertMineArea(payload: MineAreaUpsertDto): Promise<MineAreaDto> {
  return request<MineAreaDto>("/mine-area", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function downloadAnalysisReport(runId: number): Promise<Blob> {
  const res = await fetch(`${API_BASE_URL}/analysis-runs/${encodeURIComponent(String(runId))}/report`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return await res.blob();
}

export async function getLatestImagery(): Promise<ImagerySceneDto> {
  return request<ImagerySceneDto>("/imagery/latest");
}

export type StacIngestJobDto = {
  collection?: string;
  max_items?: number;
  cloud_cover_lte?: number | null;
};

export async function runStacIngestJob(payload: StacIngestJobDto = {}): Promise<ImagerySceneDto[]> {
  return request<ImagerySceneDto[]>("/jobs/ingest-stac", {
    method: "POST",
    body: JSON.stringify({
      collection: payload.collection ?? "sentinel-2-l2a",
      max_items: payload.max_items ?? 10,
      cloud_cover_lte: payload.cloud_cover_lte ?? 20,
    }),
  });
}

export async function listImageryScenes(limit = 50): Promise<ImagerySceneDto[]> {
  return request<ImagerySceneDto[]>(`/imagery?limit=${encodeURIComponent(String(limit))}`);
}
