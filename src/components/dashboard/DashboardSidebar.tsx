import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Map,
  Bell,
  FileText,
  Settings,
  Satellite,
  TrendingUp,
  Mountain,
  LogOut
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'map', label: 'Map View', icon: Map },
  { id: 'imagery', label: 'Satellite Imagery', icon: Satellite },
  { id: 'analysis', label: 'Change Analysis', icon: TrendingUp },
  { id: 'alerts', label: 'Alerts', icon: Bell, badge: 3 },
  { id: 'reports', label: 'Reports', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
];

interface DashboardSidebarProps {
  activeItem?: string;
  onItemClick?: (id: string) => void;
}

export function DashboardSidebar({
  activeItem = 'dashboard',
  onItemClick
}: DashboardSidebarProps) {
  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="sidebar-nav w-64 h-full flex flex-col text-sidebar-foreground"
    >
      {/* Logo */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
            <Mountain className="w-6 h-6 text-accent" />
          </div>
          <div>
            <h1 className="font-semibold text-lg text-white">MineWatch</h1>
            <p className="text-xs text-sidebar-foreground/60">Environmental Monitoring</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item, index) => {
          const isActive = activeItem === item.id;
          const Icon = item.icon;

          return (
            <motion.button
              key={item.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
              onClick={() => onItemClick?.(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                isActive
                  ? "bg-sidebar-accent text-white"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-white"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span className={cn(
                  "px-2 py-0.5 rounded-full text-xs font-semibold",
                  isActive
                    ? "bg-accent text-white"
                    : "bg-alert-zone/20 text-alert-zone"
                )}>
                  {item.badge}
                </span>
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border space-y-1">
        <button className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-white transition-all">
          <LogOut className="w-5 h-5" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* User info */}
      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-accent/30 flex items-center justify-center">
            <span className="text-sm font-semibold text-accent">JD</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">John Davis</p>
            <p className="text-xs text-sidebar-foreground/60 truncate">Environmental Officer</p>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
