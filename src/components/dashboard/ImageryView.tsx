import { motion } from 'framer-motion';
import { Satellite, Calendar, Cloud, Link as LinkIcon, RefreshCw } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getLatestImagery, runStacIngestJob, listImageryScenes } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from '@/hooks/use-toast';

export function ImageryView() {
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

    const scenes = scenesQuery.data ?? [];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Satellite Imagery</h2>
                    <p className="text-muted-foreground">Manage and ingestion satellite data scenes from Sentinel-2 & Landsat.</p>
                </div>
                <Button
                    onClick={() => ingestMutation.mutate()}
                    disabled={ingestMutation.isPending}
                    className="gap-2"
                >
                    <RefreshCw className={ingestMutation.isPending ? "animate-spin w-4 h-4" : "w-4 h-4"} />
                    Search & Ingest Scenes
                </Button>
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
                    scenes.map((scene, index) => (
                        <motion.div
                            key={scene.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                        >
                            <Card className="hover:border-accent/30 transition-colors">
                                <CardContent className="p-4 flex items-center gap-6">
                                    <div className="w-16 h-16 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                                        <Satellite className="w-8 h-8 text-accent" />
                                    </div>
                                    <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Source</p>
                                            <p className="text-sm font-semibold">{scene.source}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Acquisition Date</p>
                                            <div className="flex items-center gap-1.5 text-sm">
                                                <Calendar className="w-3.5 h-3.5" />
                                                {new Date(scene.acquired_at).toLocaleDateString()}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Cloud Cover</p>
                                            <div className="flex items-center gap-1.5 text-sm">
                                                <Cloud className="w-3.5 h-3.5" />
                                                {scene.cloud_cover !== null ? `${scene.cloud_cover.toFixed(1)}%` : 'n/a'}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Scene ID</p>
                                            <div className="flex items-center gap-1.5 text-sm font-mono truncate">
                                                <LinkIcon className="w-3.5 h-3.5" />
                                                {scene.uri || `mw-scene-${scene.id}`}
                                            </div>
                                        </div>
                                    </div>
                                    <Button variant="ghost" size="sm">Details</Button>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}
