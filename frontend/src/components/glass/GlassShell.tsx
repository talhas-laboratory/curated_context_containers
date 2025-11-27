'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface GlassShellProps {
  sidebar?: ReactNode;
  children: ReactNode;
  headline?: string;
  description?: string;
}

const navLinks = [
  { href: '/containers', label: 'Containers' },
  { href: '/chat-sandbox', label: 'Sandbox' },
];

export function GlassShell({ sidebar, children, headline, description }: GlassShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen relative">
      {/* Floating Nav Capsule */}
      <div className="fixed top-6 left-0 right-0 z-50 flex justify-center pointer-events-none">
        <motion.nav 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="glass-panel rounded-full px-2 py-2 flex items-center gap-1 pointer-events-auto"
        >
          <div className="px-4 font-serif italic text-ink-1 font-medium border-r border-line-2 pr-4 mr-1">
            Latent Containers
          </div>
          {navLinks.map((link) => {
            const active = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`relative px-4 py-1.5 rounded-full text-sm transition-colors duration-200 ${
                  active ? 'text-ink-1 font-medium' : 'text-ink-2 hover:text-ink-1 hover:bg-white/40'
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="nav-pill"
                    className="absolute inset-0 bg-white shadow-sm rounded-full -z-10"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                {link.label}
              </Link>
            );
          })}
        </motion.nav>
      </div>

      <main className="pt-32 px-6 pb-24 max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-8">
          {sidebar && (
            <aside className="hidden lg:block w-80 shrink-0">
              <div className="sticky top-32 space-y-6">
                 {sidebar}
              </div>
            </aside>
          )}
          
          <div className="flex-1 min-w-0">
            {(headline || description) && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-12 text-center lg:text-left"
              >
                {headline && <h1 className="text-4xl md:text-5xl text-ink-1 mb-3 font-medium tracking-tight">{headline}</h1>}
                {description && <p className="text-lg text-ink-2 max-w-2xl font-light leading-relaxed">{description}</p>}
              </motion.div>
            )}
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}

