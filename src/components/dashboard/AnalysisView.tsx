import { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Activity, BarChart3, Info, Loader2, Play, AlertTriangle, Waves, Mountain, ShieldAlert, Download, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from "date-fns";
import { TrendChart } from "./TrendChart";
import {
    createAnalysisRun,
    listImageryScenes,
    getLatestAnalysisStats,
    AnalysisRunDto,
    listAnalysisRuns,
    getAnalysisRun,
    listImageryScenesSimple,
} from "@/lib/api";
import { SceneSelector } from './SceneSelector';
import { toast } from '@/hooks/use-toast';

export function AnalysisView() {
    const [baselineSceneId, setBaselineSceneId] = useState<number | null>(null);
    const [latestSceneId, setLatestSceneId] = useState<number | null>(null);

    const { data: latestRun, isLoading, refetch: refetchLatestRun } = useQuery({
        queryKey: ['latestAnalysisRun'],
        queryFn: async () => {
            const runs = await listAnalysisRuns(1);
            if (runs.length === 0) return null;
            return getAnalysisRun(runs[0].id);
        }
    });

    const { data: scenes = [], isLoading: scenesLoading } = useQuery({
        queryKey: ['scenes', 'simple'],
        queryFn: () => listImageryScenesSimple(20)
    });

    const analysisMutation = useMutation({
        mutationFn: () => createAnalysisRun({
            baseline_scene_id: baselineSceneId ?? undefined,
            latest_scene_id: latestSceneId ?? undefined
        }),
        onSuccess: () => {
            toast({
                title: 'Analysis Started',
                description: 'New change detection analysis is being processed.'
            });
            setBaselineSceneId(null);
            setLatestSceneId(null);
            void refetchLatestRun();
        },
        onError: (err) => {
            toast({
                title: 'Analysis Failed',
                description: err instanceof Error ? err.message : 'Unable to start analysis.',
                variant: 'destructive'
            });
        }
    });

    const getValidationError = (): string | null => {
        if (!baselineSceneId || !latestSceneId) return null;

        const baseline = scenes.find(s => s.id === baselineSceneId);
        const latest = scenes.find(s => s.id === latestSceneId);

        if (!baseline || !latest) return null;

        if (baseline.id === latest.id) {
            return 'Baseline and latest scenes must be different';
        }

        const baselineDate = new Date(baseline.acquired_at);
        const latestDate = new Date(latest.acquired_at);

        if (baselineDate >= latestDate) {
            return 'Baseline scene must be acquired before latest scene';
        }

        const daysDiff = (latestDate.getTime() - baselineDate.getTime()) / (1000 * 60 * 60 * 24);
        if (daysDiff < 7) {
            return 'Warning: Scenes are less than 7 days apart - changes may be minimal';
        }

        return null;
    };

    const validationError = getValidationError();
    const canRunAnalysis = baselineSceneId && latestSceneId && !validationError?.includes('must');

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

            {/* Scene Selection Panel */}
            <Card className="border-primary/20 bg-primary/5">
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <Play className="w-4 h-4" />
                        Configure New Analysis Run
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <SceneSelector
                            label="Baseline Scene"
                            value={baselineSceneId}
                            onChange={setBaselineSceneId}
                            scenes={scenes}
                            disabled={scenesLoading}
                            helperText="Select the earlier scene for comparison"
                        />
                        <SceneSelector
                            label="Latest Scene"
                            value={latestSceneId}
                            onChange={setLatestSceneId}
                            scenes={scenes}
                            disabled={scenesLoading}
                            helperText="Select the most recent scene"
                        />
                    </div>

                    {validationError && (
                        <div className="flex items-start gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-md">
                            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                            <p className="text-sm text-amber-700 dark:text-amber-400">{validationError}</p>
                        </div>
                    )}

                    <div className="flex items-center justify-between pt-2">
                        <p className="text-xs text-muted-foreground">
                            {scenes.length === 0 ? 'No scenes available. Run STAC ingestion first.' : `${scenes.length} scene(s) available`}
                        </p>
                        <Button
                            onClick={() => analysisMutation.mutate()}
                            disabled={!canRunAnalysis || analysisMutation.isPending}
                            className="gap-2"
                        >
                            {analysisMutation.isPending ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4" />
                                    Run Analysis
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-vegetation" />
                            Spectral Index Trends (NDVI, NDWI, BSI)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <TrendChart />
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
