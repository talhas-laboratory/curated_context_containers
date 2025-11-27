import type { Meta, StoryObj } from '@storybook/react';
import { DiagnosticsRail } from '../components/DiagnosticsRail';

const meta: Meta<typeof DiagnosticsRail> = {
  title: 'Components/DiagnosticsRail',
  component: DiagnosticsRail,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof DiagnosticsRail>;

const sampleDiagnostics = {
  mode: 'hybrid',
  bm25_hits: 15,
  vector_hits: 12,
  latency_budget_ms: 900,
  latency_over_budget_ms: 0,
  containers: ['expressionist-art'],
};

const sampleTimings = {
  embed_ms: 45,
  vector_ms: 23,
  bm25_ms: 12,
  fusion_ms: 5,
  total_ms: 85,
};

const sampleGoldenSummary = {
  timestamp: '2025-11-09T12:00:00Z',
  queries: [
    {
      id: 'q1',
      query: 'what did kandinsky believe about color',
      returned: 8,
      total_hits: 47,
      avg_latency_ms: 142,
    },
    {
      id: 'q2',
      query: 'define expressionism vs impressionism',
      returned: 5,
      total_hits: 23,
      avg_latency_ms: 98,
    },
  ],
  sql_checks: {
    expressionist_art: {
      chunk_count: 1834,
      embedding_cache_rows: 142,
    },
  },
};

export const Default: Story = {
  args: {
    diagnostics: sampleDiagnostics,
    timings: sampleTimings,
    visible: true,
  },
};

export const WithGoldenSummary: Story = {
  args: {
    diagnostics: sampleDiagnostics,
    timings: sampleTimings,
    goldenSummary: sampleGoldenSummary,
    visible: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Shows golden query results with chunk counts and cache statistics'
      }
    }
  }
};

export const LatencyWarning: Story = {
  args: {
    diagnostics: {
      ...sampleDiagnostics,
      latency_over_budget_ms: 150,
    },
    timings: {
      ...sampleTimings,
      total_ms: 1050,
    },
    visible: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Latency over budget shows warning badge with ember color'
      }
    }
  }
};

export const Collapsed: Story = {
  args: {
    diagnostics: sampleDiagnostics,
    timings: sampleTimings,
    visible: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'Panel collapsed to 0 width with smooth animation'
      }
    }
  }
};

export const NoHits: Story = {
  args: {
    diagnostics: {
      ...sampleDiagnostics,
      bm25_hits: 0,
      vector_hits: 0,
    },
    timings: sampleTimings,
    visible: true,
  },
  parameters: {
    docs: {
      description: {
        story: 'Zero hits shows warning state with suggestions'
      }
    }
  }
};
