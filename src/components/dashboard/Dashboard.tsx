import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Trees,
  Layers3,
  AlertTriangle,
  CalendarDays,
  Download,
  RefreshCw,
  ChevronDown
} from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { DashboardSidebar } from './DashboardSidebar';
import { MapView } from './MapView';
import { StatCard } from './StatCard';
import { AlertItem } from './AlertItem';
import { LayerControl } from './LayerControl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/hooks/use-toast';
import { createAnalysisRun, downloadAnalysisReport, getLatestImagery, getMineArea, listAlerts, runStacIngestJob, upsertMineArea } from '@/lib/api';

const initialLayers = [
  { id: 'baseline', name: 'Baseline (Jan 2024)', description: 'Reference imagery', color: '#0d9488', enabled: true },
  { id: 'latest', name: 'Latest (Jan 2025)', description: 'Most recent capture', color: '#3b82f6', enabled: true },
  { id: 'changes', name: 'Change Detection', description: 'NDVI difference overlay', color: '#f97316', enabled: true },
  { id: 'boundary', name: 'Lease Boundary', description: 'Mining permit area', color: '#22c55e', enabled: true },
  { id: 'alerts', name: 'Alert Zones', description: 'Flagged areas', color: '#ef4444', enabled: true },
];

export function Dashboard() {
  const [activeNav, setActiveNav] = useState('dashboard');
  const [layers, setLayers] = useState(initialLayers);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const didInitRunRef = useRef(false);
  const [bufferKm, setBufferKm] = useState<string>('2');
  const [boundaryText, setBoundaryText] = useState<string>('');

  const alertsQuery = useQuery({
    queryKey: ['alerts'],
    queryFn: () => listAlerts(50),
  });

  const downloadReportMutation = useMutation({
    mutationFn: async () => {
      if (!currentRunId) {
        throw new Error('No analysis run available');
      }
      const blob = await downloadAnalysisReport(currentRunId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `minewatch-report-run-${currentRunId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast({ title: 'Report downloaded', description: 'PDF report generated successfully.' });
    },
    onError: (err) => {
      toast({ title: 'Report failed', description: err instanceof Error ? err.message : 'Unable to generate report.' });
    },
  });

  const mineAreaQuery = useQuery({
    queryKey: ['mine-area'],
    queryFn: () => getMineArea(),
    retry: false,
  });

  const latestImageryQuery = useQuery({
    queryKey: ['imagery', 'latest'],
    queryFn: () => getLatestImagery(),
    retry: false,
  });

  const ingestMutation = useMutation({
    mutationFn: () => runStacIngestJob({ max_items: 10, cloud_cover_lte: 20 }),
    onSuccess: () => {
      toast({ title: 'Ingestion complete', description: 'STAC scenes ingested successfully.' });
      void latestImageryQuery.refetch();
    },
    onError: (err) => {
      toast({ title: 'Ingestion failed', description: err instanceof Error ? err.message : 'Unable to ingest imagery.' });
    },
  });

  useEffect(() => {
    if (!mineAreaQuery.data) return;
    setBufferKm(String(mineAreaQuery.data.buffer_km));
    setBoundaryText(JSON.stringify(mineAreaQuery.data.boundary, null, 2));
  }, [mineAreaQuery.data]);

  const createRunMutation = useMutation({
    mutationFn: () => createAnalysisRun({}),
    onSuccess: (run) => {
      setCurrentRunId(run.id);
      void alertsQuery.refetch();
    },
  });

  const saveMineAreaMutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(boundaryText || '{}');
      const km = Number(bufferKm);
      if (!Number.isFinite(km) || km < 0) {
        throw new Error('Invalid buffer distance');
      }
      return upsertMineArea({ name: 'Mine Area', boundary: parsed, buffer_km: km });
    },
    onSuccess: () => {
      toast({ title: 'Saved', description: 'Mine area configuration saved.' });
      void mineAreaQuery.refetch();
    },
  });

  useEffect(() => {
    if (didInitRunRef.current) return;
    didInitRunRef.current = true;
    createRunMutation.mutate();
  }, [createRunMutation]);

  const handleLayerToggle = (layerId: string) => {
    setLayers(prev =>
      prev.map(layer =>
        layer.id === layerId
          ? { ...layer, enabled: !layer.enabled }
          : layer
      )
    );
  };

  const showChanges = layers.find(l => l.id === 'changes')?.enabled ?? true;
  const showAlerts = layers.find(l => l.id === 'alerts')?.enabled ?? true;
  const showBoundary = layers.find(l => l.id === 'boundary')?.enabled ?? true;

  const alerts = alertsQuery.data ?? [];

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <DashboardSidebar activeItem={activeNav} onItemClick={setActiveNav} />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Mpape Crushed Rock Project</h1>
            <p className="text-sm text-muted-foreground">Abuja • FCT, Nigeria</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="gap-2">
              <CalendarDays className="w-4 h-4" />
              Last 30 Days
              <ChevronDown className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => createRunMutation.mutate()}
              disabled={createRunMutation.isPending}
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
            <Button
              size="sm"
              className="gap-2 bg-accent text-accent-foreground hover:bg-accent/90"
              onClick={() => downloadReportMutation.mutate()}
              disabled={downloadReportMutation.isPending || !currentRunId}
            >
              <Download className="w-4 h-4" />
              Generate Report
            </Button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main content area */}
          <div className="flex-1 p-6 overflow-y-auto">
            {/* Stats row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard
                title="Monitored Area"
                value="2,450"
                unit="hectares"
                icon={<Layers3 className="w-5 h-5" />}
                variant="info"
                delay={0}
              />
              <StatCard
                title="Vegetation Coverage"
                value="68.4"
                unit="%"
                change={{ value: 2.3, type: 'decrease' }}
                icon={<Trees className="w-5 h-5" />}
                variant="vegetation"
                delay={0.1}
              />
              <StatCard
                title="Disturbed Land"
                value="324"
                unit="hectares"
                change={{ value: 5.1, type: 'increase' }}
                icon={<Layers3 className="w-5 h-5" />}
                variant="barren"
                delay={0.2}
              />
              <StatCard
                title="Active Alerts"
                value={String(alerts.length)}
                icon={<AlertTriangle className="w-5 h-5" />}
                variant="alert"
                delay={0.3}
              />
            </div>

            {/* Map */}
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="map-container h-[500px] mb-6"
            >
              <MapView
                showChanges={showChanges}
                showAlerts={showAlerts}
                showBoundary={showBoundary}
                runId={currentRunId}
                mineAreaBoundary={mineAreaQuery.data?.boundary ?? null}
                bufferKm={mineAreaQuery.data?.buffer_km ?? null}
              />
            </motion.div>

            {/* Alerts section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-foreground">Recent Alerts</h2>
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  View All
                </Button>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                {alerts.map((alert, index) => (
                  <AlertItem
                    key={alert.id}
                    id={String(alert.id)}
                    type={alert.type as any}
                    title={alert.title}
                    description={alert.description}
                    location={alert.location}
                    timestamp={alert.created_at}
                    severity={alert.severity as any}
                    delay={0.5 + index * 0.1}
                  />
                ))}
              </div>
            </motion.div>
          </div>

          {/* Right sidebar */}
          <aside className="w-80 border-l border-border bg-card/30 p-4 overflow-y-auto hidden lg:block">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Mine Area Setup</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="buffer-km">Buffer (km)</Label>
                  <Input
                    id="buffer-km"
                    type="number"
                    value={bufferKm}
                    onChange={(e) => setBufferKm(e.target.value)}
                    min={0}
                    step={0.1}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="boundary-file">Boundary GeoJSON file</Label>
                  <Input
                    id="boundary-file"
                    type="file"
                    accept=".geojson,application/geo+json,application/json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const reader = new FileReader();
                      reader.onload = () => {
                        const text = typeof reader.result === 'string' ? reader.result : '';
                        setBoundaryText(text);
                      };
                      reader.readAsText(file);
                    }}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="boundary-text">Boundary GeoJSON (paste)</Label>
                  <Textarea
                    id="boundary-text"
                    value={boundaryText}
                    onChange={(e) => setBoundaryText(e.target.value)}
                    placeholder="Paste a GeoJSON Polygon or FeatureCollection here"
                    className="min-h-[140px] font-mono text-xs"
                  />
                </div>

                <Button
                  className="w-full"
                  onClick={() => saveMineAreaMutation.mutate()}
                  disabled={saveMineAreaMutation.isPending}
                >
                  Save Mine Area
                </Button>
              </CardContent>
            </Card>

            <LayerControl layers={layers} onToggle={handleLayerToggle} />

            {/* Quick stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="mt-6 bg-card border border-border rounded-xl p-4"
            >
              <h3 className="font-medium text-sm text-foreground mb-4">Latest Analysis</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">NDVI Score</span>
                    <span className="font-medium text-foreground">0.42</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-vegetation rounded-full" style={{ width: '42%' }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Cloud Cover</span>
                    <span className="font-medium text-foreground">12%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-info rounded-full" style={{ width: '12%' }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Data Freshness</span>
                    <span className="font-medium text-foreground">98%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-accent rounded-full" style={{ width: '98%' }} />
                  </div>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Last updated: Jan 21, 2025 at 14:32 UTC
              </p>
            </motion.div>

            {/* Imagery info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
              className="mt-6 bg-card border border-border rounded-xl p-4"
            >
              <h3 className="font-medium text-sm text-foreground mb-3">Satellite Source</h3>
              <div className="flex items-center gap-3 p-3 bg-secondary/50 rounded-lg">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-lg">🛰️</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {latestImageryQuery.data?.source ?? 'No imagery registered'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {latestImageryQuery.data
                      ? `Acquired: ${latestImageryQuery.data.acquired_at} • Cloud: ${latestImageryQuery.data.cloud_cover ?? 'n/a'}%`
                      : 'Register or ingest imagery to enable real comparisons'}
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="mt-3 w-full"
                onClick={() => ingestMutation.mutate()}
                disabled={ingestMutation.isPending}
              >
                Ingest via STAC
              </Button>
            </motion.div>
          </aside>
        </div>
      </main>
    </div>
  );
}
