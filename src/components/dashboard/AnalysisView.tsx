import { motion } from 'framer-motion';
import { TrendingUp, Activity, BarChart3, Info, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useQuery } from '@tanstack/react-query';
import { listAnalysisRuns, getAnalysisRun } from '@/lib/api';

export function AnalysisView() {
    const { data: latestRun, isLoading } = useQuery({
        queryKey: ['latestAnalysisRun'],
        queryFn: async () => {
            const runs = await listAnalysisRuns(1);
            if (runs.length === 0) return null;
            return getAnalysisRun(runs[0].id);
        }
    });

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center p-12">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    const zones = latestRun?.zones.features || [];
    const stats = zones.reduce((acc, f) => {
        const type = f.properties?.zone_type as string;
        const area = f.properties?.area_ha as number;
        acc[type] = (acc[type] || 0) + area;
        return acc;
    }, {} as Record<string, number>);

    const totalDisturbed = Object.values(stats).reduce((a, b) => a + b, 0);

    // For demo purposes and visual balance, we define some baseline types
    const vegLoss = stats['vegetation_loss'] || 0;
    const miningExpansion = stats['mining_expansion'] || 0;
    const waterChanges = stats['water_accumulation'] || 0;

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-foreground">Change Analysis & Trends</h2>
                <p className="text-muted-foreground">Statistical breakdown of spatial changes and environmental health indicators over time.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-vegetation" />
                            NDVI Trend (Normalized Difference Vegetation Index)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[300px] w-full bg-secondary/20 rounded-lg flex items-center justify-center border border-dashed border-border p-6">
                            <div className="text-center">
                                <BarChart3 className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
                                <p className="text-sm text-muted-foreground">Interactive trend charts require additional time-series data ingestions.</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">
                                    {latestRun ? `Latest Analysis: ${new Date(latestRun.run.created_at).toLocaleDateString()}` : 'No analysis runs yet.'}
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm font-medium flex items-center gap-2">
                                <Activity className="w-4 h-4 text-info" />
                                Land Disturbance Split (Hectares)
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!latestRun ? (
                                <p className="text-xs text-muted-foreground text-center py-4">No data available from latest run.</p>
                            ) : (
                                <div className="space-y-4">
                                    <div>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">Vegetation Loss</span>
                                            <span className="font-semibold">{vegLoss.toFixed(2)} ha</span>
                                        </div>
                                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${Math.min(100, (vegLoss / (totalDisturbed || 1)) * 100)}%` }}
                                                className="h-full bg-vegetation"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">Mining Expansion</span>
                                            <span className="font-semibold">{miningExpansion.toFixed(2)} ha</span>
                                        </div>
                                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${Math.min(100, (miningExpansion / (totalDisturbed || 1)) * 100)}%` }}
                                                className="h-full bg-accent"
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">Water Accumulation</span>
                                            <span className="font-semibold">{waterChanges.toFixed(2)} ha</span>
                                        </div>
                                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${Math.min(100, (waterChanges / (totalDisturbed || 1)) * 100)}%` }}
                                                className="h-full bg-alert-zone"
                                            />
                                        </div>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground pt-2 border-t border-border">
                                        Total Area Analyzed: {totalDisturbed.toFixed(2)} hectares
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card className="bg-primary/5 border-primary/20">
                        <CardContent className="pt-6">
                            <div className="flex gap-4">
                                <Info className="w-5 h-5 text-primary shrink-0" />
                                <div className="space-y-1">
                                    <p className="text-sm font-medium text-primary">Compliance Status: {totalDisturbed > 1.0 ? 'Action Required' : 'Nominal'}</p>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        {totalDisturbed > 0
                                            ? `Detected ${totalDisturbed.toFixed(2)} ha of total spatial change. Cross-reference with authorized lease boundaries.`
                                            : "No significant spatial disturbances detected in the latest analysis cycle."}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
