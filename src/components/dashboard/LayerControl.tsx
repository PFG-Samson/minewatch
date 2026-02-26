import { motion } from 'framer-motion';
import { Layers } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';

interface Layer {
  id: string;
  name: string;
  description: string;
  color: string;
  enabled: boolean;
}

interface LayerControlProps {
  layers: Layer[];
  onToggle: (layerId: string) => void;
  compact?: boolean;
}

export function LayerControl({ layers, onToggle, compact = false }: LayerControlProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn(
        "bg-card border border-border rounded-lg",
        compact ? "p-2" : "p-4"
      )}
    >
      <div className={cn("flex items-center gap-2", compact ? "mb-2" : "mb-4")}>
        <Layers className={cn("text-muted-foreground", compact ? "w-3 h-3" : "w-4 h-4")} />
        <h3 className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>Map Layers</h3>
      </div>
      
      <div className={cn(compact ? "space-y-2" : "space-y-3")}>
        {layers.map((layer, index) => (
          <motion.div
            key={layer.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: index * 0.05 }}
            className={cn(
              "flex items-center justify-between rounded-md border transition-colors",
              compact ? "p-2" : "p-3",
              layer.enabled 
                ? "bg-secondary/50 border-border" 
                : "bg-muted/30 border-transparent"
            )}
          >
            <div className="flex items-center gap-3">
              <div 
                className={cn("rounded-full flex-shrink-0", compact ? "w-2 h-2" : "w-3 h-3")}
                style={{ backgroundColor: layer.color }}
              />
              <div>
                <p className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>
                  {layer.name}
                </p>
                <p className={cn("text-muted-foreground", compact ? "text-[10px]" : "text-xs")}>
                  {layer.description}
                </p>
              </div>
            </div>
            <Switch
              checked={layer.enabled}
              onCheckedChange={() => onToggle(layer.id)}
              className={cn("data-[state=checked]:bg-accent", compact ? "scale-90" : "")}
            />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
