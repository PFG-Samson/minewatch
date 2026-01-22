import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Sample mine boundary polygon (approximate coordinates for demo)
const MINE_BOUNDARY: [number, number][] = [
  [-23.55, 119.75],
  [-23.52, 119.80],
  [-23.54, 119.85],
  [-23.58, 119.83],
  [-23.60, 119.78],
  [-23.57, 119.74],
];

// Sample change detection zones
const CHANGE_ZONES = [
  {
    id: 1,
    type: 'vegetation_loss',
    coords: [[-23.545, 119.77], [-23.54, 119.78], [-23.55, 119.79], [-23.555, 119.775]] as [number, number][],
    area: 12.5,
  },
  {
    id: 2,
    type: 'vegetation_gain',
    coords: [[-23.57, 119.80], [-23.565, 119.815], [-23.575, 119.82], [-23.58, 119.805]] as [number, number][],
    area: 8.3,
  },
  {
    id: 3,
    type: 'alert',
    coords: [[-23.59, 119.76], [-23.585, 119.77], [-23.595, 119.775], [-23.60, 119.765]] as [number, number][],
    area: 3.2,
  },
];

interface MapViewProps {
  showBaseline?: boolean;
  showLatest?: boolean;
  showChanges?: boolean;
  showAlerts?: boolean;
}

export function MapView({ 
  showBaseline = true, 
  showLatest = true, 
  showChanges = true, 
  showAlerts = true 
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersRef = useRef<{
    boundary?: L.Polygon;
    buffer?: L.Polygon;
    changes: L.Polygon[];
  }>({ changes: [] });

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Initialize map centered on mine area
    const map = L.map(mapRef.current, {
      center: [-23.56, 119.79],
      zoom: 13,
      zoomControl: true,
      attributionControl: true,
    });

    // Add satellite tile layer
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 18,
    }).addTo(map);

    // Add mine boundary
    const boundary = L.polygon(MINE_BOUNDARY, {
      color: '#0d9488',
      weight: 3,
      fillColor: '#0d9488',
      fillOpacity: 0.1,
      dashArray: '10, 5',
    }).addTo(map);
    layersRef.current.boundary = boundary;

    // Add buffer zone (5km approximation)
    const bufferCoords = MINE_BOUNDARY.map(([lat, lng]) => [
      lat + (Math.random() - 0.5) * 0.03 - 0.02,
      lng + (Math.random() - 0.5) * 0.04 - 0.02,
    ] as [number, number]);
    
    const buffer = L.polygon([
      [-23.50, 119.70],
      [-23.48, 119.88],
      [-23.62, 119.90],
      [-23.65, 119.72],
    ], {
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

  // Handle layer visibility
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing change zones
    layersRef.current.changes.forEach(layer => map.removeLayer(layer));
    layersRef.current.changes = [];

    if (showChanges || showAlerts) {
      CHANGE_ZONES.forEach(zone => {
        if (zone.type === 'alert' && !showAlerts) return;
        if (zone.type !== 'alert' && !showChanges) return;

        const color = zone.type === 'vegetation_loss' 
          ? '#c2410c' 
          : zone.type === 'vegetation_gain' 
            ? '#16a34a' 
            : '#dc2626';

        const polygon = L.polygon(zone.coords, {
          color: color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.4,
        }).addTo(map);

        polygon.bindPopup(`
          <div style="font-family: Inter, sans-serif; padding: 4px;">
            <strong style="font-size: 14px; color: ${color};">
              ${zone.type === 'vegetation_loss' ? '🔻 Vegetation Loss' : zone.type === 'vegetation_gain' ? '🌱 Vegetation Gain' : '⚠️ Alert Zone'}
            </strong>
            <p style="margin: 8px 0 0; font-size: 13px; color: #475569;">
              Area: <strong>${zone.area} hectares</strong>
            </p>
          </div>
        `);

        layersRef.current.changes.push(polygon);
      });
    }
  }, [showChanges, showAlerts]);

  return (
    <div 
      ref={mapRef} 
      className="w-full h-full min-h-[400px] rounded-xl"
      style={{ background: 'hsl(var(--muted))' }}
    />
  );
}
