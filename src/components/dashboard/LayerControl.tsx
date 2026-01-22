import { motion } from 'framer-motion';
import { Layers, Eye, EyeOff } from 'lucide-react';
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
}

export function LayerControl({ layers, onToggle }: LayerControlProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-card border border-border rounded-xl p-4"
    >
      <div className="flex items-center gap-2 mb-4">
        <Layers className="w-4 h-4 text-muted-foreground" />
        <h3 className="font-medium text-sm text-foreground">Map Layers</h3>
      </div>
      
      <div className="space-y-3">
        {layers.map((layer, index) => (
          <motion.div
            key={layer.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: index * 0.05 }}
            className={cn(
              "flex items-center justify-between p-3 rounded-lg border transition-colors",
              layer.enabled 
                ? "bg-secondary/50 border-border" 
                : "bg-muted/30 border-transparent"
            )}
          >
            <div className="flex items-center gap-3">
              <div 
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: layer.color }}
              />
              <div>
                <p className="text-sm font-medium text-foreground">
                  {layer.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {layer.description}
                </p>
              </div>
            </div>
            <Switch
              checked={layer.enabled}
              onCheckedChange={() => onToggle(layer.id)}
              className="data-[state=checked]:bg-accent"
            />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
