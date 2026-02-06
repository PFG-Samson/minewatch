import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getAnalysisRun, getRunImagery, type GeoJsonFeatureCollection, type RunImageryDto } from '@/lib/api';

// Mpape Crushed Rock Quarry area coordinates
const MINE_BOUNDARY: [number, number][] = [
  [9.138, 7.490],
  [9.140, 7.495],
  [9.135, 7.500],
  [9.130, 7.498],
  [9.128, 7.492],
  [9.132, 7.488],
];

interface MapViewProps {
  showBaseline?: boolean;
  showLatest?: boolean;
  showChanges?: boolean;
  showAlerts?: boolean;
  showBoundary?: boolean;
  runId?: number | null;
  mineAreaBoundary?: Record<string, unknown> | null;
  bufferKm?: number | null;
}

export function MapView({
  showBaseline = true,
  showLatest = true,
  showChanges = true,
  showAlerts = true,
  showBoundary = true,
  runId = null,
  mineAreaBoundary = null,
  bufferKm = null,
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const [zones, setZones] = useState<GeoJsonFeatureCollection | null>(null);
  const [imagery, setImagery] = useState<RunImageryDto | null>(null);
  const lastBoundaryKeyRef = useRef<string | null>(null);
  const layersRef = useRef<{
    boundary?: L.Layer;
    buffer?: L.Layer;
    extent?: L.Rectangle;
    zonesLayer?: L.GeoJSON;
    baselineImagery?: L.ImageOverlay;
    latestImagery?: L.ImageOverlay;
  }>({});

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!runId) {
        setZones(null);
        setImagery(null);
        return;
      }

      try {
        const [analysisData, imageryData] = await Promise.all([
          getAnalysisRun(runId),
          getRunImagery(runId)
        ]);

        if (cancelled) return;
        setZones(analysisData.zones);
        setImagery(imageryData);
      } catch (e) {
        console.error("Failed to load map data", e);
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Update Imagery Layers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.baselineImagery) {
      map.removeLayer(layersRef.current.baselineImagery);
      layersRef.current.baselineImagery = undefined;
    }
    if (layersRef.current.latestImagery) {
      map.removeLayer(layersRef.current.latestImagery);
      layersRef.current.latestImagery = undefined;
    }

    if (imagery?.baseline && showBaseline) {
      const { url, bounds } = imagery.baseline;
      layersRef.current.baselineImagery = L.imageOverlay(`http://localhost:8000${url}`, [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]]
      ], { opacity: 1.0 }).addTo(map);
    }

    if (imagery?.latest && showLatest) {
      const { url, bounds } = imagery.latest;
      layersRef.current.latestImagery = L.imageOverlay(`http://localhost:8000${url}`, [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]]
      ], { opacity: 1.0 }).addTo(map);
    }
  }, [imagery, showBaseline, showLatest]);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Initialize map centered on mine area
    const map = L.map(mapRef.current, {
      center: [9.135, 7.493],
      zoom: 15,
      zoomControl: true,
      attributionControl: true,
    });

    // Add satellite tile layer
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 18,
    }).addTo(map);

    // Default boundary + buffer (can be replaced by saved mine area GeoJSON)
    const boundary = L.polygon(MINE_BOUNDARY, {
      color: '#0d9488',
      weight: 3,
      fillColor: '#0d9488',
      fillOpacity: 0.1,
      dashArray: '10, 5',
    }).addTo(map);
    layersRef.current.boundary = boundary;

    const center = boundary.getBounds().getCenter();
    const buffer = L.circle(center, {
      radius: 2000,
      color: '#64748b',
      weight: 2,
      fillColor: '#64748b',
      fillOpacity: 0.05,
      dashArray: '5, 10',
    }).addTo(map);
    layersRef.current.buffer = buffer;

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.boundary) {
      map.removeLayer(layersRef.current.boundary);
      layersRef.current.boundary = undefined;
    }
    if (layersRef.current.buffer) {
      map.removeLayer(layersRef.current.buffer);
      layersRef.current.buffer = undefined;
    }
    if (layersRef.current.extent) {
      map.removeLayer(layersRef.current.extent);
      layersRef.current.extent = undefined;
    }

    if (!showBoundary) return;

    const boundaryLayer = mineAreaBoundary
      ? L.geoJSON(mineAreaBoundary as any, {
        style: {
          color: '#0d9488',
          weight: 3,
          fillColor: '#0d9488',
          fillOpacity: 0.1,
          dashArray: '10, 5',
        },
      })
      : L.polygon(MINE_BOUNDARY, {
        color: '#0d9488',
        weight: 3,
        fillColor: '#0d9488',
        fillOpacity: 0.1,
        dashArray: '10, 5',
      });

    boundaryLayer.addTo(map);
    layersRef.current.boundary = boundaryLayer;

    const bounds = (boundaryLayer as any).getBounds?.();
    if (bounds) {
      const rect = L.rectangle(bounds, {
        color: '#22c55e',
        weight: 1,
        fillOpacity: 0,
        dashArray: '4, 6',
      });
      rect.addTo(map);
      layersRef.current.extent = rect;

      const boundaryKey = mineAreaBoundary ? JSON.stringify(mineAreaBoundary) : null;
      if (boundaryKey && boundaryKey !== lastBoundaryKeyRef.current) {
        lastBoundaryKeyRef.current = boundaryKey;
        map.fitBounds(bounds.pad(0.2));
      }
    }

    const km = typeof bufferKm === 'number' && Number.isFinite(bufferKm) ? bufferKm : 2;
    const center = bounds?.getCenter ? bounds.getCenter() : L.latLng(9.135, 7.493);

    const bufferLayer = L.circle(center, {
      radius: km * 1000,
      color: '#64748b',
      weight: 2,
      fillColor: '#64748b',
      fillOpacity: 0.05,
      dashArray: '5, 10',
    }).addTo(map);
    layersRef.current.buffer = bufferLayer;
  }, [mineAreaBoundary, bufferKm, showBoundary]);

  // Handle layer visibility
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (layersRef.current.zonesLayer) {
      map.removeLayer(layersRef.current.zonesLayer);
      layersRef.current.zonesLayer = undefined;
    }

    if (!zones) return;

    const filtered: GeoJsonFeatureCollection = {
      type: 'FeatureCollection',
      features: zones.features.filter((f) => {
        const zoneType = String(f.properties?.zone_type ?? '');
        if (zoneType === 'alert') return showAlerts;
        return showChanges;
      }),
    };

    const zonesLayer = L.geoJSON(filtered as any, {
      style: (feature: any) => {
        const zoneType = String(feature?.properties?.zone_type ?? '');
        let color = '#dc2626'; // Default red

        if (zoneType === 'vegetation_loss') color = '#c2410c'; // Orange/Brown
        else if (zoneType === 'vegetation_gain') color = '#16a34a'; // Green
        else if (zoneType === 'mining_expansion') color = '#7c3aed'; // Purple
        else if (zoneType === 'water_accumulation') color = '#2563eb'; // Blue

        return {
          color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.4,
        } as L.PathOptions;
      },
      onEachFeature: (feature: any, layer) => {
        const zoneType = String(feature?.properties?.zone_type ?? '');
        const areaHa = feature?.properties?.area_ha;

        const labels: Record<string, string> = {
          'vegetation_loss': '🔻 Vegetation Loss',
          'vegetation_gain': '🌱 Vegetation Gain',
          'mining_expansion': '🚜 Mining Expansion',
          'water_accumulation': '💧 Water Accumulation',
          'alert': '⚠️ Alert Zone'
        };

        layer.bindPopup(`
          <div style="font-family: Inter, sans-serif; padding: 4px; min-width: 140px;">
            <strong style="font-size: 14px; display: block; margin-bottom: 4px;">
              ${labels[zoneType] || 'Unknown Zone'}
            </strong>
            <p style="margin: 4px 0; font-size: 13px; color: #475569;">
              Area: <strong>${areaHa ? areaHa.toFixed(2) : 'n/a'} ha</strong>
            </p>
          </div>
        `);
      },
    }).addTo(map);

    layersRef.current.zonesLayer = zonesLayer;
  }, [showChanges, showAlerts, zones]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full min-h-[400px] rounded-xl"
      style={{ background: 'hsl(var(--muted))' }}
    />
  );
}
