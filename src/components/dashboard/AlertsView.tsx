import { motion } from 'framer-motion';
import { AlertTriangle, Filter, Search } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { listAlerts } from '@/lib/api';
import { AlertItem } from './AlertItem';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';

export function AlertsView() {
    const [search, setSearch] = useState('');
    const alertsQuery = useQuery({
        queryKey: ['alerts', 'full'],
        queryFn: () => listAlerts(100),
    });

    const alerts = (alertsQuery.data ?? []).filter(a =>
        a.title.toLowerCase().includes(search.toLowerCase()) ||
        a.location.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Alert History</h2>
                    <p className="text-muted-foreground">Comprehensive log of all environmental monitoring alerts and security flags.</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                            placeholder="Search alerts..."
                            className="pl-9 w-[250px]"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                    <Button variant="outline" size="icon">
                        <Filter className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {alertsQuery.isLoading ? (
                <div className="py-12 text-center text-muted-foreground">Loading alert history...</div>
            ) : alerts.length === 0 ? (
                <div className="py-20 flex flex-col items-center border border-dashed rounded-xl">
                    <AlertTriangle className="w-12 h-12 text-muted-foreground/30 mb-4" />
                    <p className="text-lg font-medium">No alerts found</p>
                    <p className="text-sm text-muted-foreground">Wait for the next analysis run or adjust your filters.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
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
                            delay={index * 0.05}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
