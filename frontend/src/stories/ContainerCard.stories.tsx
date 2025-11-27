import type { Meta, StoryObj } from '@storybook/react';
import { ContainerCard } from '../components/ContainerCard';

const meta: Meta<typeof ContainerCard> = {
  title: 'Components/ContainerCard',
  component: ContainerCard,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof ContainerCard>;

const sampleContainer = {
  id: 'expressionist-art',
  name: 'Expressionist Art',
  theme: 'German Expressionism',
  modalities: ['text', 'image'],
  state: 'active' as const,
  stats: {
    document_count: 142,
    chunk_count: 1834,
    size_mb: 234.5,
    last_ingest: '2025-11-08T23:50:00Z',
  },
  created_at: '2025-11-01T12:00:00Z',
  updated_at: '2025-11-08T23:50:00Z',
};

export const Default: Story = {
  args: {
    container: sampleContainer,
  },
};

export const Paused: Story = {
  args: {
    container: {
      ...sampleContainer,
      state: 'paused' as const,
    },
  },
};

export const Archived: Story = {
  args: {
    container: {
      ...sampleContainer,
      state: 'archived' as const,
    },
  },
};

export const NoStats: Story = {
  args: {
    container: {
      ...sampleContainer,
      stats: undefined,
    },
  },
};

export const SingleModality: Story = {
  args: {
    container: {
      ...sampleContainer,
      modalities: ['text'],
    },
  },
};

