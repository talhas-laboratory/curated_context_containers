import React from 'react';

type ModeOption = {
  label: string;
  value: string;
};

interface GraphModeToggleProps {
  options: ModeOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function GraphModeToggle({ options, value, onChange, disabled }: GraphModeToggleProps) {
  return (
    <div
      className="flex gap-2 bg-white/40 rounded-full p-1 backdrop-blur-sm border border-white/30"
      role="group"
      aria-label="Search mode"
    >
      {options.map((m) => (
        <button
          key={m.value}
          type="button"
          onClick={() => !disabled && onChange(m.value)}
          aria-pressed={value === m.value}
          disabled={disabled}
          className={`px-4 py-1.5 rounded-full text-sm transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/20 ${
            value === m.value ? 'bg-ink-1 text-white shadow-sm' : 'text-ink-2 hover:text-ink-1'
          } ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
