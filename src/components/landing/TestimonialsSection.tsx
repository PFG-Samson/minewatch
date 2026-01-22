import { motion } from 'framer-motion';
import { Quote } from 'lucide-react';

const testimonials = [
  {
    quote: "MineWatch replaced three full-time GIS analysts and cut our reporting time from weeks to hours. The automated alerts caught an unauthorized expansion we would have missed.",
    author: "Sarah Mitchell",
    role: "Environmental Manager",
    company: "Northern Mining Corp",
  },
  {
    quote: "Finally, a monitoring solution that understands compliance requirements. The reports are audit-ready and the data trail is impeccable.",
    author: "James Chen",
    role: "Chief Sustainability Officer", 
    company: "Mineral Resources Ltd",
  },
  {
    quote: "We used to fly drones monthly for vegetation surveys. Now satellite analysis runs automatically and we only deploy drones for verification. Massive cost savings.",
    author: "David Okonkwo",
    role: "Site Manager",
    company: "West Africa Mining",
  },
];

export function TestimonialsSection() {
  return (
    <section className="py-24 bg-secondary/30">
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
            Trusted by Industry Leaders
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground">
            What Mining Professionals Say
          </h2>
        </motion.div>

        {/* Testimonials grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.15 }}
              className="relative p-6 rounded-2xl bg-card border border-border"
            >
              <Quote className="w-8 h-8 text-accent/20 mb-4" />
              <p className="text-foreground/90 leading-relaxed mb-6">
                "{testimonial.quote}"
              </p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                  <span className="text-sm font-semibold text-accent">
                    {testimonial.author.split(' ').map(n => n[0]).join('')}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-foreground">{testimonial.author}</p>
                  <p className="text-sm text-muted-foreground">
                    {testimonial.role}, {testimonial.company}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
