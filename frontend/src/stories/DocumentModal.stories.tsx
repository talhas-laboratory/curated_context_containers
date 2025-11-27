import type { Meta, StoryObj } from '@storybook/react';
import { DocumentModal } from '../components/DocumentModal';

const meta: Meta<typeof DocumentModal> = {
  title: 'Components/DocumentModal',
  component: DocumentModal,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof DocumentModal>;

const sampleResult = {
  chunk_id: 'chunk-123',
  doc_id: 'doc-456',
  container_id: 'expressionist-art',
  container_name: 'Expressionist Art',
  title: 'Kandinsky — Concerning the Spiritual in Art',
  snippet:
    'Kandinsky argued that color directly influences the soul and that abstract forms can evoke the deepest emotions. His treatise explores the psychological impact of saturated hues, particularly the IKB spectrum, which he believed could access spiritual dimensions beyond mere visual perception.',
  uri: 's3://containers/expressionist-art/doc-456/original/kandinsky.pdf',
  score: 0.87,
  modality: 'text' as const,
  provenance: {
    source: 'url',
    ingested_at: '2025-11-08T18:00:00Z',
    modality: 'text',
    page: 12,
  },
  meta: {
    author: 'Wassily Kandinsky',
    tags: ['color', 'expressionism', 'spiritual'],
    period: 'modernism',
    confidence: 0.93,
  },
};

export const Default: Story = {
  args: {
    result: sampleResult,
    isOpen: true,
    onClose: () => {},
  },
};

export const WithImage: Story = {
  args: {
    result: {
      ...sampleResult,
      modality: 'image' as const,
      uri: 's3://containers/expressionist-art/doc-456/original/kandinsky-painting.jpg',
    },
    isOpen: true,
    onClose: () => {},
  },
};

export const MinimalMetadata: Story = {
  args: {
    result: {
      chunk_id: 'chunk-789',
      doc_id: 'doc-101',
      container_id: 'test-container',
      title: 'Untitled Document',
      snippet: 'Basic content without extensive metadata.',
      score: 0.65,
      modality: 'text' as const,
    },
    isOpen: true,
    onClose: () => {},
  },
};

export const Closed: Story = {
  args: {
    result: sampleResult,
    isOpen: false,
    onClose: () => {},
  },
};

