import { motion } from 'framer-motion';
import { TrendingUp, Activity, BarChart3, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function AnalysisView() {
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
                                <p className="text-xs text-muted-foreground/60 mt-1">Current data point: 0.42 (Healthy Sparsity)</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm font-medium flex items-center gap-2">
                                <Activity className="w-4 h-4 text-info" />
                                Land Disturbance Split
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-muted-foreground">Natural Vegetation</span>
                                        <span className="font-semibold">68%</span>
                                    </div>
                                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                        <div className="h-full bg-vegetation" style={{ width: '68%' }} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-muted-foreground">Modified Landscape</span>
                                        <span className="font-semibold">22%</span>
                                    </div>
                                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                        <div className="h-full bg-accent" style={{ width: '22%' }} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-muted-foreground">Active Pits / Infrastructure</span>
                                        <span className="font-semibold">10%</span>
                                    </div>
                                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                        <div className="h-full bg-alert-zone" style={{ width: '10%' }} />
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-primary/5 border-primary/20">
                        <CardContent className="pt-6">
                            <div className="flex gap-4">
                                <Info className="w-5 h-5 text-primary shrink-0" />
                                <div className="space-y-1">
                                    <p className="text-sm font-medium text-primary">Compliance Status: Warning</p>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        Detected cumulative vegetation loss exceeds the seasonal baseline by 5.2%.
                                        Verify restorative progress in Sector East.
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
