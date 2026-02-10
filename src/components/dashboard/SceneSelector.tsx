import { ImagerySceneDto } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Cloud, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface SceneSelectorProps {
    label: string;
    value: number | null;
    onChange: (sceneId: number) => void;
    scenes: ImagerySceneDto[];
    disabled?: boolean;
    helperText?: string;
}

export function SceneSelector({
    label,
    value,
    onChange,
    scenes,
    disabled = false,
    helperText
}: SceneSelectorProps) {
    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch {
            return dateStr;
        }
    };

    const getCloudCoverBadge = (cloudCover: number | null) => {
        if (cloudCover === null) return null;

        if (cloudCover < 10) {
            return <Badge variant="outline" className="ml-2 text-xs bg-green-500/10 text-green-600">Clear</Badge>;
        } else if (cloudCover < 30) {
            return <Badge variant="outline" className="ml-2 text-xs bg-blue-500/10 text-blue-600">{cloudCover.toFixed(0)}%</Badge>;
        } else {
            return <Badge variant="outline" className="ml-2 text-xs bg-orange-500/10 text-orange-600">{cloudCover.toFixed(0)}%</Badge>;
        }
    };

    return (
        <div className="space-y-2">
            <Label htmlFor={`scene-${label}`} className="text-sm font-medium">
                {label}
            </Label>

            <Select
                value={value?.toString() ?? ''}
                onValueChange={(val) => onChange(parseInt(val, 10))}
                disabled={disabled}
            >
                <SelectTrigger id={`scene-${label}`} className="w-full">
                    <SelectValue placeholder="Select a scene..." />
                </SelectTrigger>

                <SelectContent>
                    {scenes.length === 0 ? (
                        <div className="p-4 text-center text-sm text-muted-foreground">
                            No scenes available. Run STAC ingestion first.
                        </div>
                    ) : (
                        scenes.map((scene) => (
                            <SelectItem key={scene.id} value={scene.id.toString()}>
                                <div className="flex items-center justify-between w-full gap-3">
                                    <div className="flex items-center gap-2">
                                        <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                                        <span className="font-medium">{formatDate(scene.acquired_at)}</span>
                                    </div>

                                    <div className="flex items-center gap-1">
                                        {scene.cloud_cover !== null && (
                                            <>
                                                <Cloud className="w-3.5 h-3.5 text-muted-foreground" />
                                                {getCloudCoverBadge(scene.cloud_cover)}
                                            </>
                                        )}
                                    </div>
                                </div>
                            </SelectItem>
                        ))
                    )}
                </SelectContent>
            </Select>

            {helperText && (
                <p className="text-xs text-muted-foreground">{helperText}</p>
            )}

            {value && scenes.length > 0 && (
                <div className="text-xs text-muted-foreground mt-1">
                    {(() => {
                        const selectedScene = scenes.find(s => s.id === value);
                        if (selectedScene) {
                            return (
                                <div className="flex items-center gap-2">
                                    <span>Source: {selectedScene.source}</span>
                                    {selectedScene.cloud_cover !== null && (
                                        <span>• Cloud Cover: {selectedScene.cloud_cover.toFixed(1)}%</span>
                                    )}
                                </div>
                            );
                        }
                        return null;
                    })()}
                </div>
            )}
        </div>
    );
}
