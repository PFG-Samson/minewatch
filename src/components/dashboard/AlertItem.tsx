import { motion } from 'framer-motion';
import { AlertTriangle, TrendingDown, MapPin, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertItemProps {
  id: string;
  type: 'vegetation_loss' | 'boundary_breach' | 'threshold_exceeded';
  title: string;
  description: string;
  location: string;
  timestamp: string;
  severity: 'high' | 'medium' | 'low';
  delay?: number;
  geometry?: Record<string, unknown> | null;
  onLocationClick?: () => void;
}

const severityStyles = {
  high: {
    bg: 'bg-alert-zone/10',
    border: 'border-alert-zone/30',
    icon: 'text-alert-zone',
    badge: 'bg-alert-zone/15 text-alert-zone',
  },
  medium: {
    bg: 'bg-warning/10',
    border: 'border-warning/30',
    icon: 'text-warning',
    badge: 'bg-warning/15 text-warning',
  },
  low: {
    bg: 'bg-info/10',
    border: 'border-info/30',
    icon: 'text-info',
    badge: 'bg-info/15 text-info',
  },
};

const typeIcons = {
  vegetation_loss: TrendingDown,
  boundary_breach: MapPin,
  threshold_exceeded: AlertTriangle,
};

export function AlertItem({
  type,
  title,
  description,
  location,
  timestamp,
  severity,
  delay = 0,
  geometry,
  onLocationClick
}: AlertItemProps) {
  const styles = severityStyles[severity];
  const Icon = typeIcons[type];

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay }}
      className={cn(
        "p-4 rounded-lg border",
        styles.bg,
        styles.border
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn("mt-0.5 flex-shrink-0", styles.icon)}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-sm text-foreground truncate">
              {title}
            </h4>
            <span className={cn(
              "flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium uppercase tracking-wide",
              styles.badge
            )}>
              {severity}
            </span>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
            {description}
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {location}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {timestamp}
            </span>
          </div>
          {geometry && onLocationClick && (
            <button
              onClick={onLocationClick}
              className="mt-2 px-3 py-1.5 text-xs font-medium rounded-md bg-primary/10 hover:bg-primary/20 text-primary transition-colors flex items-center gap-1.5"
            >
              <MapPin className="w-3 h-3" />
              View on Map
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
