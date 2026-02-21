import { useQuery } from "@tanstack/react-query";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";
import { CardTitle, CardDescription } from "@/components/ui/card";
import { format } from "date-fns";
import { Loader2, TrendingUp, AlertCircle } from "lucide-react";
import { listAnalysisTrends, AnalysisTrendDto } from "@/lib/api";

export function TrendChart() {
    const { data, isLoading, error } = useQuery<AnalysisTrendDto[]>({
        queryKey: ["analysis-trends"],
        queryFn: () => listAnalysisTrends(),
    });

    if (isLoading) {
        return (
            <div className="flex h-[300px] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="flex h-[300px] flex-col items-center justify-center text-muted-foreground">
                <AlertCircle className="mb-2 h-10 w-10 opacity-20" />
                <p>Could not load trend data</p>
            </div>
        );
    }

    // Filter out items with missing or invalid dates to prevent RangeError
    const validData = data.filter(item => {
        if (!item.date) return false;
        const d = new Date(item.date);
        return !isNaN(d.getTime());
    });

    if (validData.length === 0) {
        return (
            <div className="flex h-[300px] flex-col items-center justify-center border-2 border-dashed rounded-lg bg-muted/50 p-6 text-center">
                <div className="mb-4 rounded-full bg-primary/10 p-3 text-primary">
                    <TrendingUp className="h-6 w-6" />
                </div>
                <CardTitle className="mb-2">No Valid Trend Data</CardTitle>
                <CardDescription>
                    Analysis runs are missing date mapping. Run a new analysis to begin tracking.
                </CardDescription>
            </div>
        );
    }

    const safeFormat = (dateStr: string, formatStr: string) => {
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return "Invalid Date";
            return format(d, formatStr);
        } catch (e) {
            return "N/A";
        }
    };

    if (validData.length === 1) {
        const single = validData[0];
        return (
            <div className="flex h-[300px] flex-col items-center justify-center border-2 border-dashed rounded-lg bg-muted/50 p-6 text-center">
                <div className="mb-4 rounded-full bg-primary/10 p-3 text-primary">
                    <TrendingUp className="h-6 w-6" />
                </div>
                <CardTitle className="mb-2">Baseline Captured</CardTitle>
                <div className="flex gap-4 mb-4 text-sm">
                    <div className="flex flex-col">
                        <span className="text-muted-foreground">NDVI</span>
                        <span className="font-mono font-bold text-green-600">{single.ndvi.toFixed(3)}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-muted-foreground">NDWI</span>
                        <span className="font-mono font-bold text-blue-600">{single.ndwi.toFixed(3)}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-muted-foreground">BSI</span>
                        <span className="font-mono font-bold text-orange-600">{single.bsi.toFixed(3)}</span>
                    </div>
                </div>
                <CardDescription>
                    One analysis complete ({safeFormat(single.date, "MMM d, yyyy")}).
                    <br /> Perform a second analysis to see the trend lines.
                </CardDescription>
            </div>
        );
    }

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={validData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                    <XAxis
                        dataKey="date"
                        tickFormatter={(str) => safeFormat(str, "MMM d")}
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        domain={[-1, 1]}
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => val.toFixed(1)}
                    />
                    <Tooltip
                        labelFormatter={(label) => safeFormat(label, "MMMM d, yyyy")}
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                    <Line
                        type="monotone"
                        dataKey="ndvi"
                        name="Vegetation (NDVI)"
                        stroke="#22c55e"
                        strokeWidth={2}
                        dot={{ r: 4, fill: "#22c55e" }}
                        activeDot={{ r: 6 }}
                    />
                    <Line
                        type="monotone"
                        dataKey="ndwi"
                        name="Water (NDWI)"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ r: 4, fill: "#3b82f6" }}
                    />
                    <Line
                        type="monotone"
                        dataKey="bsi"
                        name="Soil (BSI)"
                        stroke="#f97316"
                        strokeWidth={2}
                        dot={{ r: 4, fill: "#f97316" }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
