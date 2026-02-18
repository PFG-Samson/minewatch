import { motion } from 'framer-motion';
import { FileText, Download, CheckCircle2, AlertCircle } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { downloadAnalysisReport, listAnalysisRuns, AnalysisRunDto } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { toast } from '@/hooks/use-toast';

export function ReportsView({ currentRunId }: { currentRunId: number | null }) {
    const downloadMutation = useMutation({
        mutationFn: async (runId: number) => {
            const blob = await downloadAnalysisReport(runId);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `minewatch-report-run-${runId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        },
        onSuccess: (_data, variables) => {
            toast({ title: 'Report generated', description: `PDF for run #${variables} has been downloaded.` });
        },
        onError: (err) => {
            toast({ title: 'Download failed', description: err instanceof Error ? err.message : 'Unable to generate PDF report.' });
        },
    });

    const runsQuery = useQuery<AnalysisRunDto[]>({
        queryKey: ['analysisRuns', 10],
        queryFn: () => listAnalysisRuns(10),
        staleTime: 30_000,
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Compliance Reports</h2>
                    <p className="text-muted-foreground">Download audit-ready documentation and generated environmental assessments.</p>
                </div>
                <Button
                    onClick={() => {
                        if (currentRunId) {
                            downloadMutation.mutate(currentRunId);
                        } else {
                            toast({ title: 'No active run', description: 'Start or refresh an analysis run to download its report.' });
                        }
                    }}
                    disabled={downloadMutation.isPending || !currentRunId}
                    className="gap-2"
                >
                    <FileText className="w-4 h-4" />
                    Download Current Report
                </Button>
            </div>

            <div className="grid grid-cols-1 gap-3">
                {runsQuery.isLoading && (
                    <div className="text-sm text-muted-foreground px-2 py-1">Loading recent analysis runs…</div>
                )}

                {runsQuery.isError && (
                    <div className="mt-2 flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                        <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-amber-500">Unable to load runs</p>
                            <p className="text-xs text-amber-500/70 mt-1">Please check server connectivity and try again.</p>
                        </div>
                    </div>
                )}

                {runsQuery.data?.map((run, index) => {
                    const created = new Date(run.created_at);
                    const dateStr = created.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
                    const statusLabel = run.status === 'completed' ? 'Audit Ready' : run.status;
                    return (
                        <motion.div
                            key={run.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                        >
                            <Card>
                                <CardContent className="p-4 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                            <FileText className="w-5 h-5 text-primary" />
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold">Analysis Run #{run.id}</h3>
                                            <p className="text-xs text-muted-foreground">Generated on {dateStr}</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4">
                                        <div className="flex items-center gap-1.5 text-xs text-vegetation">
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                            {statusLabel}
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="gap-2 px-3"
                                            onClick={() => downloadMutation.mutate(run.id)}
                                            disabled={downloadMutation.isPending}
                                        >
                                            <Download className="w-3.5 h-3.5" />
                                            Download PDF
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    );
                })}

                {!currentRunId && (
                    <div className="mt-6 flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                        <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-amber-500">No active analysis session</p>
                            <p className="text-xs text-amber-500/70 mt-1">
                                You need to start or refresh an analysis run to generate a live report for the current site state.
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
