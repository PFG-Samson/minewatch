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
import { createAnalysisRun, downloadAnalysisReport, getLatestImagery, getMineArea, listAlerts, runStacIngestJob, upsertMineArea, getLatestAnalysisStats } from '@/lib/api';
import { ImageryView } from './ImageryView';
import { AlertsView } from './AlertsView';
import { AnalysisView } from './AnalysisView';
import { ReportsView } from './ReportsView';

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
  const [siteName, setSiteName] = useState<string>('');
  const [siteDescription, setSiteDescription] = useState<string>('');
  const [previewBoundary, setPreviewBoundary] = useState<Record<string, unknown> | null>(null);
  const [selectedAlertGeometry, setSelectedAlertGeometry] = useState<Record<string, unknown> | null>(null);

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

  const statsQuery = useQuery({
    queryKey: ['analysis', 'stats'],
    queryFn: () => getLatestAnalysisStats(),
    retry: false,
    refetchInterval: 30000, // Refresh every 30s
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
    setSiteName(mineAreaQuery.data.name);
    setSiteDescription(mineAreaQuery.data.description || '');
  }, [mineAreaQuery.data]);

  // Effect to parse boundary text for on-the-fly preview
  useEffect(() => {
    if (!boundaryText) {
      setPreviewBoundary(null);
      return;
    }
    try {
      const parsed = JSON.parse(boundaryText);
      setPreviewBoundary(parsed);
    } catch (e) {
      // Silently fail preview on malformed JSON while typing
      setPreviewBoundary(null);
    }
  }, [boundaryText]);

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
      return upsertMineArea({
        name: siteName || 'Mine Area',
        description: siteDescription,
        boundary: parsed,
        buffer_km: km
      });
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
            <h1 className="text-xl font-semibold text-foreground">{siteName || 'Mine Project'}</h1>
            <p className="text-sm text-muted-foreground">{mineAreaQuery.data ? 'Monitoring Site' : 'New Configuration'}</p>
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
            {activeNav === 'dashboard' && (
              <>
                {/* Stats row */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <StatCard
                    title="Monitored Area"
                    value={mineAreaQuery.data?.area_ha?.toFixed(2) || "0"}
                    unit="hectares"
                    icon={<Layers3 className="w-5 h-5" />}
                    variant="info"
                    delay={0}
                  />
                  <StatCard
                    title="Vegetation Loss"
                    value={statsQuery.data?.vegetation_loss_ha?.toFixed(2) || "0"}
                    unit="hectares"
                    icon={<Trees className="w-5 h-5" />}
                    variant="alert"
                    delay={0.1}
                  />
                  <StatCard
                    title="Vegetation Gain"
                    value={statsQuery.data?.vegetation_gain_ha?.toFixed(2) || "0"}
                    unit="hectares"
                    icon={<Trees className="w-5 h-5" />}
                    variant="vegetation"
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
                    previewBoundary={previewBoundary}
                    bufferKm={Number(bufferKm) || null}
                    highlightedGeometry={activeNav === 'map' ? selectedAlertGeometry : null}
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
                    <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setActiveNav('alerts')}>
                      View All
                    </Button>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                    {alerts.slice(0, 3).map((alert, index) => (
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
                        geometry={alert.geometry}
                        onLocationClick={() => {
                          setSelectedAlertGeometry(alert.geometry || null);
                          setActiveNav('map');
                        }}
                      />
                    ))}
                  </div>
                </motion.div>
              </>
            )}

            {activeNav === 'map' && (
              <div className="h-full flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-foreground">Full Map View</h2>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setLayers(initialLayers)}>Reset Layers</Button>
                  </div>
                </div>
                <div className="flex-1 rounded-xl overflow-hidden border border-border shadow-inner relative">
                  <MapView
                    showChanges={showChanges}
                    showAlerts={showAlerts}
                    showBoundary={showBoundary}
                    runId={currentRunId}
                    mineAreaBoundary={mineAreaQuery.data?.boundary ?? null}
                    previewBoundary={previewBoundary}
                    bufferKm={Number(bufferKm) || null}
                    highlightedGeometry={selectedAlertGeometry}
                  />
                  <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-sm p-3 rounded-lg border border-border z-[1000] w-64 shadow-lg">
                    <LayerControl layers={layers} onToggle={handleLayerToggle} />
                  </div>
                </div>
              </div>
            )}

            {activeNav === 'imagery' && <ImageryView />}
            {activeNav === 'analysis' && <AnalysisView />}
            {activeNav === 'alerts' && <AlertsView />}
            {activeNav === 'reports' && <ReportsView currentRunId={currentRunId} />}

            {activeNav === 'settings' && (
              <div className="max-w-4xl mx-auto space-y-8">
                <div>
                  <h2 className="text-3xl font-bold text-foreground mb-2">Project Settings</h2>
                  <p className="text-muted-foreground">Configure your mine lease boundary and monitoring parameters.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <Card>
                      <CardHeader>
                        <CardTitle>Core Configuration</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="s-site-name">Project Name</Label>
                          <Input
                            id="s-site-name"
                            value={siteName}
                            onChange={(e) => setSiteName(e.target.value)}
                            placeholder="e.g. Northern Mine Lease"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="s-description">Description</Label>
                          <Textarea
                            id="s-description"
                            value={siteDescription}
                            onChange={(e) => setSiteDescription(e.target.value)}
                            placeholder="Describe the project scope and location..."
                            className="min-h-[80px]"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="s-buffer-km">Monitoring Buffer (km)</Label>
                          <Input
                            id="s-buffer-km"
                            type="number"
                            value={bufferKm}
                            onChange={(e) => setBufferKm(e.target.value)}
                            min={0}
                            step={0.1}
                          />
                          <p className="text-xs text-muted-foreground">The system will analyze STAC imagery within this radius of your boundary center.</p>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle>Boundary Definition</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="s-boundary-file">Upload GeoJSON</Label>
                          <Input
                            id="s-boundary-file"
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
                        <div className="space-y-2">
                          <Label htmlFor="s-boundary-text">Manual GeoJSON (WGS84)</Label>
                          <Textarea
                            id="s-boundary-text"
                            value={boundaryText}
                            onChange={(e) => setBoundaryText(e.target.value)}
                            placeholder="Paste a GeoJSON Polygon or FeatureCollection here"
                            className="min-h-[200px] font-mono text-xs"
                          />
                        </div>
                      </CardContent>
                    </Card>

                    <Button
                      size="lg"
                      className="w-full"
                      onClick={() => saveMineAreaMutation.mutate()}
                      disabled={saveMineAreaMutation.isPending}
                    >
                      {saveMineAreaMutation.isPending ? 'Saving...' : 'Save Configuration'}
                    </Button>
                  </div>

                  <div className="space-y-6">
                    <Card className="h-full">
                      <CardHeader>
                        <CardTitle>Boundary Preview</CardTitle>
                      </CardHeader>
                      <CardContent className="h-[400px] p-0 overflow-hidden rounded-b-xl border-t">
                        <MapView
                          showChanges={false}
                          showAlerts={false}
                          showBoundary={true}
                          mineAreaBoundary={mineAreaQuery.data?.boundary ?? null}
                          previewBoundary={previewBoundary}
                          bufferKm={Number(bufferKm) || null}
                        />
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right sidebar - Only show on dashboard and hidden on map */}
          {activeNav === 'dashboard' && (
            <aside className="w-80 border-l border-border bg-card/30 p-4 overflow-y-auto hidden lg:block">
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
                      <span className="text-muted-foreground">Vegetation Loss</span>
                      <span className="font-medium text-foreground">
                        {statsQuery.data?.vegetation_loss_ha?.toFixed(2) || '0.00'} ha
                      </span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-alert-zone rounded-full" style={{ width: `${Math.min((statsQuery.data?.vegetation_loss_ha || 0) * 20, 100)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Vegetation Gain</span>
                      <span className="font-medium text-foreground">
                        {statsQuery.data?.vegetation_gain_ha?.toFixed(2) || '0.00'} ha
                      </span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-vegetation rounded-full" style={{ width: `${Math.min((statsQuery.data?.vegetation_gain_ha || 0) * 20, 100)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Mining Expansion</span>
                      <span className="font-medium text-foreground">
                        {statsQuery.data?.mining_expansion_ha?.toFixed(2) || '0.00'} ha
                      </span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-barren rounded-full" style={{ width: `${Math.min((statsQuery.data?.mining_expansion_ha || 0) * 20, 100)}%` }} />
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-4">
                  {statsQuery.data?.last_updated
                    ? `Last updated: ${new Date(statsQuery.data.last_updated).toLocaleString()}`
                    : 'No analysis data available'}
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
          )}
        </div>
      </main>
    </div>
  );
}
