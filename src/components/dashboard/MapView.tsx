import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getAnalysisRun, type GeoJsonFeatureCollection } from '@/lib/api';

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
  const lastBoundaryKeyRef = useRef<string | null>(null);
  const layersRef = useRef<{
    boundary?: L.Layer;
    buffer?: L.Layer;
    extent?: L.Rectangle;
    zonesLayer?: L.GeoJSON;
  }>({});

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!runId) {
        setZones(null);
        return;
      }

      const data = await getAnalysisRun(runId);
      if (cancelled) return;
      setZones(data.zones);
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [runId]);

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
        const color = zoneType === 'vegetation_loss'
          ? '#c2410c'
          : zoneType === 'vegetation_gain'
            ? '#16a34a'
            : '#dc2626';

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
        const color = zoneType === 'vegetation_loss'
          ? '#c2410c'
          : zoneType === 'vegetation_gain'
            ? '#16a34a'
            : '#dc2626';

        layer.bindPopup(`
          <div style="font-family: Inter, sans-serif; padding: 4px;">
            <strong style="font-size: 14px; color: ${color};">
              ${zoneType === 'vegetation_loss' ? '🔻 Vegetation Loss' : zoneType === 'vegetation_gain' ? '🌱 Vegetation Gain' : '⚠️ Alert Zone'}
            </strong>
            <p style="margin: 8px 0 0; font-size: 13px; color: #475569;">
              Area: <strong>${areaHa ?? 'n/a'} hectares</strong>
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
