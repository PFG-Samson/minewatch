import { motion } from 'framer-motion';
import { Mountain, Linkedin, Twitter, Mail } from 'lucide-react';

const footerLinks = {
  Product: ['Features', 'Pricing', 'Case Studies', 'Documentation'],
  Company: ['About', 'Careers', 'Contact', 'Partners'],
  Resources: ['Blog', 'Webinars', 'API Reference', 'Support'],
  Legal: ['Privacy Policy', 'Terms of Service', 'Security', 'Compliance'],
};

export function Footer() {
  return (
    <footer className="bg-primary text-primary-foreground">
      <div className="container mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
          {/* Logo and description */}
          <div className="col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                <Mountain className="w-6 h-6 text-accent" />
              </div>
              <span className="font-semibold text-xl">MineWatch</span>
            </div>
            <p className="text-primary-foreground/60 text-sm leading-relaxed mb-6 max-w-xs">
              Automated environmental change detection for mining operations. 
              Satellite-powered compliance monitoring.
            </p>
            <div className="flex gap-4">
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
                <Linkedin className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
                <Mail className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="font-semibold text-sm mb-4">{category}</h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link}>
                    <a 
                      href="#" 
                      className="text-sm text-primary-foreground/60 hover:text-primary-foreground transition-colors"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-primary-foreground/50">
            © 2025 MineWatch. All rights reserved.
          </p>
          <p className="text-sm text-primary-foreground/50">
            Built for mining professionals who need to prove compliance.
          </p>
        </div>
      </div>
    </footer>
  );
}
