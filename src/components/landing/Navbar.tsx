import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mountain, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Resources', href: '#resources' },
];

interface NavbarProps {
  onDemoClick?: () => void;
  variant?: 'transparent' | 'solid';
}

export function Navbar({ onDemoClick, variant = 'transparent' }: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={cn(
        "fixed top-0 left-0 right-0 z-50 px-6 py-4",
        variant === 'transparent' ? 'bg-transparent' : 'bg-background/80 backdrop-blur-md border-b border-border'
      )}
    >
      <div className="container mx-auto flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5">
          <div className={cn(
            "w-9 h-9 rounded-lg flex items-center justify-center",
            variant === 'transparent' ? 'bg-white/10' : 'bg-accent/10'
          )}>
            <Mountain className={cn(
              "w-5 h-5",
              variant === 'transparent' ? 'text-white' : 'text-accent'
            )} />
          </div>
          <span className={cn(
            "font-semibold text-lg",
            variant === 'transparent' ? 'text-white' : 'text-foreground'
          )}>
            MineWatch
          </span>
        </a>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className={cn(
                "text-sm font-medium transition-colors",
                variant === 'transparent' 
                  ? 'text-white/70 hover:text-white' 
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* CTA buttons */}
        <div className="hidden md:flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="sm"
            className={cn(
              variant === 'transparent' 
                ? 'text-white/80 hover:text-white hover:bg-white/10' 
                : ''
            )}
          >
            Sign In
          </Button>
          <Button 
            size="sm"
            onClick={onDemoClick}
            className="bg-accent text-accent-foreground hover:bg-accent/90"
          >
            Request Demo
          </Button>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className={cn(
            "md:hidden p-2 rounded-lg",
            variant === 'transparent' ? 'text-white' : 'text-foreground'
          )}
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="md:hidden absolute top-full left-0 right-0 bg-background border-b border-border p-4"
        >
          <nav className="flex flex-col gap-2">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary rounded-lg"
              >
                {link.label}
              </a>
            ))}
            <hr className="my-2 border-border" />
            <Button variant="ghost" size="sm" className="justify-start">
              Sign In
            </Button>
            <Button size="sm" onClick={onDemoClick} className="bg-accent text-accent-foreground">
              Request Demo
            </Button>
          </nav>
        </motion.div>
      )}
    </motion.header>
  );
}
