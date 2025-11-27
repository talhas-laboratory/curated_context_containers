'use client';

import { ComponentProps, forwardRef } from 'react';

interface GlassInputProps extends ComponentProps<'input'> {
  icon?: React.ReactNode;
}

export const GlassInput = forwardRef<HTMLInputElement, GlassInputProps>(
  ({ className = '', icon, ...props }, ref) => {
    const forwardedProps = { ...props } as Record<string, unknown>;
    const dataTestId = forwardedProps['data-testid'] as string | undefined;
    if ('data-testid' in forwardedProps) {
      delete forwardedProps['data-testid'];
    }

    return (
      <div className="relative group">
        <div className={`
          absolute inset-0 rounded-full bg-gradient-to-r from-blue-100/50 via-purple-100/50 to-pink-100/50 
          opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-lg -z-10
        `} />
        <div className="relative flex items-center">
          {icon && (
            <div className="absolute left-4 text-ink-2 pointer-events-none">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={`
              w-full bg-white/60 backdrop-blur-md border border-white/40 rounded-full
              px-6 py-3.5 text-ink-1 placeholder:text-ink-2/70
              shadow-sm transition-all duration-300
              focus:outline-none focus:bg-white/80 focus:shadow-glass-glow focus:border-white/60
              ${icon ? 'pl-12' : ''}
              ${className}
            `}
            data-testid={dataTestId}
            {...(forwardedProps as ComponentProps<'input'>)}
          />
        </div>
      </div>
    );
  }
);

GlassInput.displayName = 'GlassInput';

