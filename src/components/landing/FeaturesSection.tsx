import { motion } from 'framer-motion';
import {
  Satellite,
  BarChart3,
  Bell,
  FileText,
  Map,
  Shield,
  Zap,
  Cloud
} from 'lucide-react';

const features = [
  {
    icon: Satellite,
    title: 'Satellite Data Ingestion',
    description: 'Automated fetching of Sentinel-2 imagery. Cloud-free composites generated without manual intervention.',
    gradient: 'from-info to-accent',
  },
  {
    icon: BarChart3,
    title: 'Multi-Spectral Analysis',
    description: 'Track vegetation health (NDVI), monitor bare soil expansion (BSI), and detect water accumulation (NDWI) with automated trend analysis.',
    gradient: 'from-vegetation to-accent',
  },
  {
    icon: Map,
    title: 'Interactive GIS Maps',
    description: 'Toggle between baseline and current imagery. Visualize change detection overlays with pixel-level precision.',
    gradient: 'from-accent to-info',
  },
  {
    icon: Bell,
    title: 'Smart Alerts',
    description: 'Rule-based notifications for vegetation loss, boundary breaches, or threshold exceedances. Dashboard alerts.',
    gradient: 'from-warning to-alert-zone',
  },
  {
    icon: FileText,
    title: 'Compliance Reports',
    description: 'One-click PDF generation with map snapshots, area statistics, and audit-ready documentation.',
    gradient: 'from-primary to-accent',
  },
  {
    icon: Shield,
    title: 'Regulatory Ready',
    description: 'Built for ESG reporting requirements. Defensible data sources and transparent methodology.',
    gradient: 'from-accent to-vegetation',
  },
];

export function FeaturesSection() {
  return (
    <section className="py-24 bg-background">
      <div className="container mx-auto px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center max-w-2xl mx-auto mb-16"
        >
          <p className="text-sm font-medium text-accent uppercase tracking-wider mb-3">
            Platform Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Everything You Need for Environmental Compliance
          </h2>
          <p className="text-lg text-muted-foreground">
            Replace manual GIS analysis with continuous automated monitoring.
            From satellite to report, fully hands-off.
          </p>
        </motion.div>

        {/* Features grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="group relative p-6 rounded-2xl bg-card border border-border hover:border-accent/30 transition-all duration-300 hover:shadow-lg hover:shadow-accent/5"
              >
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} p-0.5 mb-5`}>
                  <div className="w-full h-full bg-card rounded-[10px] flex items-center justify-center">
                    <Icon className="w-5 h-5 text-accent" />
                  </div>
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-accent transition-colors">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>

                {/* Hover effect */}
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              </motion.div>
            );
          })}
        </div>

        {/* Bottom highlight */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-16 p-8 rounded-2xl bg-gradient-to-r from-primary to-primary/80 text-primary-foreground"
        >
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-white/10 flex items-center justify-center">
                <Zap className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-xl font-semibold"> Satellite Data</h3>
                <p className="text-primary-foreground/70">
                  Uses Sentinel-2 Imagery
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Cloud className="w-5 h-5 text-primary-foreground/60" />
              <span className="text-sm text-primary-foreground/80">
                Processed in the cloud • No local infrastructure needed
              </span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
