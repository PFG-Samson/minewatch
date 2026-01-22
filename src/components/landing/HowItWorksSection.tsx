import { motion } from 'framer-motion';
import { Upload, Satellite, BarChart2, Bell, FileText, ArrowRight } from 'lucide-react';

const steps = [
  {
    number: '01',
    icon: Upload,
    title: 'Define Your Area',
    description: 'Upload or draw your mining lease boundary and buffer zones. Store as GeoJSON for precise monitoring.',
  },
  {
    number: '02',
    icon: Satellite,
    title: 'Automatic Imagery',
    description: 'System fetches latest cloud-free Sentinel-2 imagery. No manual downloads or data management.',
  },
  {
    number: '03',
    icon: BarChart2,
    title: 'Change Detection',
    description: 'NDVI analysis compares baseline to current state. Pixel-level vegetation and land cover changes identified.',
  },
  {
    number: '04',
    icon: Bell,
    title: 'Smart Alerts',
    description: 'Threshold-based rules trigger notifications. Vegetation loss, boundary breaches, or custom conditions.',
  },
  {
    number: '05',
    icon: FileText,
    title: 'Generate Reports',
    description: 'One-click PDF reports with maps, statistics, and compliance documentation. Audit-ready.',
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 bg-secondary/20">
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
            How It Works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            From Satellite to Report in Five Steps
          </h2>
          <p className="text-lg text-muted-foreground">
            Everything flows automatically. Define your area once, then the system 
            handles imagery, analysis, alerts, and reporting.
          </p>
        </motion.div>

        {/* Steps */}
        <div className="relative">
          {/* Connection line */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-border to-transparent -translate-y-1/2" />
          
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                  className="relative group"
                >
                  {/* Step card */}
                  <div className="relative z-10 flex flex-col items-center text-center p-6 rounded-2xl bg-card border border-border hover:border-accent/30 transition-all duration-300 hover:shadow-lg">
                    {/* Number badge */}
                    <span className="absolute -top-3 -right-2 w-8 h-8 rounded-full bg-accent text-accent-foreground text-xs font-bold flex items-center justify-center">
                      {step.number}
                    </span>
                    
                    {/* Icon */}
                    <div className="w-14 h-14 rounded-xl bg-accent/10 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                      <Icon className="w-7 h-7 text-accent" />
                    </div>
                    
                    {/* Content */}
                    <h3 className="text-base font-semibold text-foreground mb-2">
                      {step.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                  
                  {/* Arrow connector (except last) */}
                  {index < steps.length - 1 && (
                    <div className="hidden lg:block absolute top-1/2 -right-3 transform -translate-y-1/2 z-20">
                      <ArrowRight className="w-6 h-6 text-border" />
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
