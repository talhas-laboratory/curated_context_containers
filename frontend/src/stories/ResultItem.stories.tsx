import type { Meta, StoryObj } from '@storybook/react';
import { ResultItem } from '../components/ResultItem';

const meta: Meta<typeof ResultItem> = {
  title: 'Components/ResultItem',
  component: ResultItem,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof ResultItem>;

const sampleResult = {
  chunk_id: 'abc123',
  doc_id: 'doc456',
  container_id: 'expressionist-art',
  container_name: 'Expressionist Art',
  title: 'Kandinsky — Concerning the Spiritual in Art',
  snippet: 'Kandinsky viewed color as having spiritual properties that could evoke deep emotional responses in the viewer. His treatise explores the psychological impact of saturated hues.',
  uri: 'https://example.com/kandinsky.pdf#page=12',
  score: 0.87,
  modality: 'text',
  provenance: {
    source: 'url',
    ingested_at: '2025-11-08T18:00:00Z',
  },
  meta: {
    author: 'Wassily Kandinsky',
    tags: ['expressionism', 'color theory'],
  },
};

export const Default: Story = {
  args: {
    result: sampleResult,
    diagnosticsVisible: false,
    onSelect: () => {},
  },
};

export const WithDiagnostics: Story = {
  args: {
    result: sampleResult,
    diagnosticsVisible: true,
    onSelect: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: 'Shows score badge with ikb-2 text, modality chip, and provenance details'
      }
    }
  }
};

export const HighScore: Story = {
  args: {
    result: {
      ...sampleResult,
      score: 0.95,
    },
    diagnosticsVisible: true,
    onSelect: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: 'Score ≥0.9 uses ikb-0 stroke for emphasis'
      }
    }
  }
};

export const WithDedup: Story = {
  args: {
    result: {
      ...sampleResult,
      meta: {
        ...sampleResult.meta,
        semantic_dedup_score: 0.92,
        duplicate_of: 'chunk789',
      },
    },
    diagnosticsVisible: true,
    onSelect: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: 'Shows dedup badge with score when semantic duplicate detected'
      }
    }
  }
};

export const Hover: Story = {
  args: {
    result: sampleResult,
    diagnosticsVisible: false,
    onSelect: () => {},
  },
  parameters: {
    pseudo: { hover: true },
    docs: {
      description: {
        story: 'Border emphasizes to line-2, 2px lift transform'
      }
    }
  }
};
