import { useState } from 'react';
import { motion } from 'framer-motion';
import { Satellite, Calendar, Cloud, Link as LinkIcon, RefreshCw, Play, CheckCircle2 } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { listImageryScenes, runStacIngestJob, createAnalysisRun } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

export function ImageryView() {
    const [baselineId, setBaselineId] = useState<number | null>(null);
    const [latestId, setLatestId] = useState<number | null>(null);

    const scenesQuery = useQuery({
        queryKey: ['imagery', 'list'],
        queryFn: () => listImageryScenes(20),
    });

    const ingestMutation = useMutation({
        mutationFn: () => runStacIngestJob({ max_items: 5, cloud_cover_lte: 15 }),
        onSuccess: () => {
            toast({ title: 'Ingestion complete', description: 'New scenes discovered and registered.' });
            void scenesQuery.refetch();
        },
        onError: (err) => {
            toast({ title: 'Ingestion failed', description: err instanceof Error ? err.message : 'Unable to ingest imagery.' });
        },
    });

    const analysisMutation = useMutation({
        mutationFn: () => createAnalysisRun({
            baseline_scene_id: baselineId ?? undefined,
            latest_scene_id: latestId ?? undefined
        }),
        onSuccess: () => {
            toast({ title: 'Analysis Started', description: 'New scientific pipeline run is being processed.' });
            setBaselineId(null);
            setLatestId(null);
        },
        onError: (err) => {
            toast({ title: 'Analysis Failed', description: err instanceof Error ? err.message : 'Unable to start run.' });
        }
    });

    const handleSelect = (id: number, type: 'baseline' | 'latest') => {
        if (type === 'baseline') {
            setBaselineId(baselineId === id ? null : id);
            if (latestId === id) setLatestId(null);
        } else {
            setLatestId(latestId === id ? null : id);
            if (baselineId === id) setBaselineId(null);
        }
    };

    const scenes = scenesQuery.data ?? [];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Satellite Imagery Catalog</h2>
                    <p className="text-muted-foreground">Select two scenes to perform a comparative scientific analysis (NDVI, NDWI, BSI).</p>
                </div>
                <div className="flex gap-3">
                    <Button
                        variant="outline"
                        onClick={() => ingestMutation.mutate()}
                        disabled={ingestMutation.isPending}
                        className="gap-2"
                    >
                        <RefreshCw className={ingestMutation.isPending ? "animate-spin w-4 h-4" : "w-4 h-4"} />
                        Sync STAC
                    </Button>
                    <Button
                        disabled={!baselineId || !latestId || analysisMutation.isPending}
                        onClick={() => analysisMutation.mutate()}
                        className="gap-2 bg-accent hover:bg-accent/90"
                    >
                        <Play className="w-4 h-4" />
                        Run Selected Analysis
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {scenesQuery.isLoading ? (
                    <div className="py-12 text-center text-muted-foreground">Loading imagery catalog...</div>
                ) : scenes.length === 0 ? (
                    <Card className="border-dashed">
                        <CardContent className="py-12 flex flex-col items-center">
                            <Satellite className="w-12 h-12 text-muted-foreground/30 mb-4" />
                            <p className="text-lg font-medium">No imagery ingested yet</p>
                            <p className="text-sm text-muted-foreground mb-6">Run a STAC ingestion job to populate your local catalog.</p>
                            <Button variant="outline" onClick={() => ingestMutation.mutate()}>Start First Ingestion</Button>
                        </CardContent>
                    </Card>
                ) : (
                    scenes.map((scene, index) => {
                        const isBaseline = baselineId === scene.id;
                        const isLatest = latestId === scene.id;

                        return (
                            <motion.div
                                key={scene.id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.05 }}
                            >
                                <Card className={cn(
                                    "transition-all duration-200 border-l-4",
                                    isBaseline ? "border-l-vegetation bg-vegetation/5" :
                                        isLatest ? "border-l-accent bg-accent/5" :
                                            "border-l-transparent hover:border-l-muted"
                                )}>
                                    <CardContent className="p-4 flex items-center gap-6">
                                        <div className="w-12 h-12 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                                            <Satellite className={cn("w-6 h-6", (isBaseline || isLatest) ? "text-primary" : "text-muted-foreground")} />
                                        </div>
                                        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div>
                                                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-0.5">Acquisition</p>
                                                <div className="flex items-center gap-1.5 text-sm font-medium">
                                                    <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                                                    {new Date(scene.acquired_at).toLocaleDateString()}
                                                </div>
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-0.5">Cloud Cover</p>
                                                <div className="flex items-center gap-1.5 text-sm">
                                                    <Cloud className="w-3.5 h-3.5 text-muted-foreground" />
                                                    {scene.cloud_cover !== null ? `${scene.cloud_cover.toFixed(1)}%` : 'n/a'}
                                                </div>
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-bold text-muted-foreground uppercase mb-0.5">Status</p>
                                                <p className="text-xs text-muted-foreground">Ready for Processing</p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Button
                                                    size="sm"
                                                    variant={isBaseline ? "default" : "outline"}
                                                    className={cn("h-8 text-xs", isBaseline && "bg-vegetation hover:bg-vegetation/90")}
                                                    onClick={() => handleSelect(scene.id, 'baseline')}
                                                >
                                                    {isBaseline && <CheckCircle2 className="w-3 h-3 mr-1" />}
                                                    Baseline
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant={isLatest ? "default" : "outline"}
                                                    className={cn("h-8 text-xs", isLatest && "bg-accent hover:bg-accent/90")}
                                                    onClick={() => handleSelect(scene.id, 'latest')}
                                                >
                                                    {isLatest && <CheckCircle2 className="w-3 h-3 mr-1" />}
                                                    Latest
                                                </Button>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
