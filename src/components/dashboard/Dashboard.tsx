import { useState } from 'react';
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
import { DashboardSidebar } from './DashboardSidebar';
import { MapView } from './MapView';
import { StatCard } from './StatCard';
import { AlertItem } from './AlertItem';
import { LayerControl } from './LayerControl';
import { Button } from '@/components/ui/button';

const mockAlerts = [
  {
    id: '1',
    type: 'vegetation_loss' as const,
    title: 'Significant vegetation loss detected',
    description: 'NDVI analysis shows 12.5 hectares of vegetation decline in the northwest sector.',
    location: 'Sector NW-3',
    timestamp: '2 hours ago',
    severity: 'high' as const,
  },
  {
    id: '2',
    type: 'boundary_breach' as const,
    title: 'Activity detected outside boundary',
    description: 'Movement patterns suggest potential unauthorized expansion near buffer zone.',
    location: 'Buffer Zone East',
    timestamp: '5 hours ago',
    severity: 'medium' as const,
  },
  {
    id: '3',
    type: 'threshold_exceeded' as const,
    title: 'Bare soil threshold exceeded',
    description: 'Current exposed soil area exceeds permitted levels by 8%.',
    location: 'Pit Area B',
    timestamp: '1 day ago',
    severity: 'low' as const,
  },
];

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

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <DashboardSidebar activeItem={activeNav} onItemClick={setActiveNav} />
      
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm">
          <div>
            <h1 className="text-xl font-semibold text-foreground">Dashboard Overview</h1>
            <p className="text-sm text-muted-foreground">Pilbara Iron Ore Project • Western Australia</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="gap-2">
              <CalendarDays className="w-4 h-4" />
              Last 30 Days
              <ChevronDown className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" className="gap-2">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
            <Button size="sm" className="gap-2 bg-accent text-accent-foreground hover:bg-accent/90">
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
                value="3"
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
                {mockAlerts.map((alert, index) => (
                  <AlertItem key={alert.id} {...alert} delay={0.5 + index * 0.1} />
                ))}
              </div>
            </motion.div>
          </div>

          {/* Right sidebar */}
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
                  <p className="text-sm font-medium text-foreground">Sentinel-2A</p>
                  <p className="text-xs text-muted-foreground">10m resolution • Multispectral</p>
                </div>
              </div>
            </motion.div>
          </aside>
        </div>
      </main>
    </div>
  );
}
