'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { layoutTokens } from '../lib/tokens';

interface ShellProps {
  sidebar?: ReactNode;
  children: ReactNode;
  headline?: string;
  description?: string;
}

const navLinks = [
  { href: '/containers', label: 'Containers' },
  { href: '/chat-sandbox', label: 'Chat Sandbox' },
];

export function Shell({ sidebar, children, headline = 'Local Latent Containers', description }: ShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-paper-0 text-ink-1">
      <header className="border-b border-line-1 bg-paper-0">
        <div className={`mx-auto flex ${layoutTokens.pageMaxWidth} items-center justify-between px-6 py-6 lg:px-10`}>
          <div>
            <h1 className="text-2xl font-light text-ink-1">{headline}</h1>
            {description && <p className="text-sm text-ink-2">{description}</p>}
          </div>
          <nav className="flex gap-3 text-sm text-ink-2">
            {navLinks.map((link) => {
              const active = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-full border px-3 py-1 transition ${
                    active
                      ? 'border-ink-1 text-ink-1'
                      : 'border-line-2 text-ink-2 hover:border-ink-1 hover:text-ink-1'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <div className={`mx-auto flex ${layoutTokens.pageMaxWidth} flex-col gap-10 ${layoutTokens.shellPadding}`}>
        {sidebar && (
          <div className="lg:hidden">
            <div className="rounded-2xl border border-line-1 bg-paper-1 p-4">{sidebar}</div>
          </div>
        )}
        <div className="flex flex-col gap-10 lg:flex-row">
          {sidebar && <aside className={`hidden flex-shrink-0 lg:block ${layoutTokens.sidebarWidth}`}>{sidebar}</aside>}
          <section className="flex-1">{children}</section>
        </div>
      </div>
    </div>
  );
}
