import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  change?: {
    value: number;
    type: 'increase' | 'decrease' | 'neutral';
  };
  icon: ReactNode;
  variant?: 'default' | 'vegetation' | 'barren' | 'alert' | 'info';
  delay?: number;
}

const variantStyles = {
  default: 'border-border',
  vegetation: 'border-l-4 border-l-vegetation border-border',
  barren: 'border-l-4 border-l-barren border-border',
  alert: 'border-l-4 border-l-alert-zone border-border',
  info: 'border-l-4 border-l-info border-border',
};

const iconBgStyles = {
  default: 'bg-secondary text-secondary-foreground',
  vegetation: 'bg-vegetation/10 text-vegetation',
  barren: 'bg-barren/10 text-barren',
  alert: 'bg-alert-zone/10 text-alert-zone',
  info: 'bg-info/10 text-info',
};

export function StatCard({ 
  title, 
  value, 
  unit, 
  change, 
  icon, 
  variant = 'default',
  delay = 0 
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn(
        "stat-card flex items-start justify-between gap-4",
        variantStyles[variant]
      )}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-muted-foreground truncate">
          {title}
        </p>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl font-semibold text-foreground">
            {value}
          </span>
          {unit && (
            <span className="text-sm text-muted-foreground">{unit}</span>
          )}
        </div>
        {change && (
          <div className="mt-2 flex items-center gap-1.5">
            <span className={cn(
              "text-xs font-medium",
              change.type === 'increase' && change.value > 0 ? 'text-alert-zone' : '',
              change.type === 'decrease' ? 'text-vegetation' : '',
              change.type === 'neutral' ? 'text-muted-foreground' : ''
            )}>
              {change.type === 'increase' ? '↑' : change.type === 'decrease' ? '↓' : '→'}
              {' '}{Math.abs(change.value)}%
            </span>
            <span className="text-xs text-muted-foreground">vs last month</span>
          </div>
        )}
      </div>
      <div className={cn(
        "flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center",
        iconBgStyles[variant]
      )}>
        {icon}
      </div>
    </motion.div>
  );
}
