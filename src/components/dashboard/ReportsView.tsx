import { motion } from 'framer-motion';
import { FileText, Download, CheckCircle2, AlertCircle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { downloadAnalysisReport } from '@/lib/api';
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
            a.download = `minewatch-report-run-current.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        },
        onSuccess: () => {
            toast({ title: 'Report generated', description: 'PDF has been downloaded.' });
        },
        onError: (err) => {
            toast({ title: 'Download failed', description: err instanceof Error ? err.message : 'Unable to generate PDF report.' });
        },
    });

    const reports = [
        { id: 1, date: '2025-01-21', type: 'Monthly Compliance', status: 'completed' },
        { id: 2, date: '2024-12-15', type: 'Quarterly ESG Report', status: 'completed' },
        { id: 3, date: '2024-11-20', type: 'Incidence Analysis', status: 'completed' },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Compliance Reports</h2>
                    <p className="text-muted-foreground">Download audit-ready documentation and generated environmental assessments.</p>
                </div>
                <Button
                    onClick={() => currentRunId && downloadMutation.mutate(currentRunId)}
                    disabled={downloadMutation.isPending || !currentRunId}
                    className="gap-2"
                >
                    <FileText className="w-4 h-4" />
                    Generate New Report
                </Button>
            </div>

            <div className="grid grid-cols-1 gap-3">
                {reports.map((report, index) => (
                    <motion.div
                        key={report.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                    >
                        <Card>
                            <CardContent className="p-4 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                        <FileText className="w-5 h-5 text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold">{report.type}</h3>
                                        <p className="text-xs text-muted-foreground">Generated on {report.date}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-1.5 text-xs text-vegetation">
                                        <CheckCircle2 className="w-3.5 h-3.5" />
                                        Audit Ready
                                    </div>
                                    <Button variant="outline" size="sm" className="gap-2 px-3">
                                        <Download className="w-3.5 h-3.5" />
                                        Download PDF
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                ))}

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
