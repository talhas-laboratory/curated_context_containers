import type { Meta, StoryObj } from '@storybook/react';
import { SearchInput } from '../components/SearchInput';

const meta: Meta<typeof SearchInput> = {
  title: 'Components/SearchInput',
  component: SearchInput,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof SearchInput>;

export const Default: Story = {
  args: {
    value: '',
    placeholder: 'Search expressionist-art...',
    diagnosticsEnabled: false,
    onToggleDiagnostics: () => {},
    onSubmit: () => {},
    loading: false,
  },
};

export const WithQuery: Story = {
  args: {
    value: 'color theory kandinsky',
    placeholder: 'Search expressionist-art...',
    diagnosticsEnabled: false,
    onToggleDiagnostics: () => {},
    onSubmit: () => {},
    loading: false,
  },
};

export const DiagnosticsEnabled: Story = {
  args: {
    value: 'expressionist use of color',
    placeholder: 'Search expressionist-art...',
    diagnosticsEnabled: true,
    onToggleDiagnostics: () => {},
    onSubmit: () => {},
    loading: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'Diagnostics pill shows active mode with ikb-1 text accent'
      }
    }
  }
};

export const Loading: Story = {
  args: {
    value: 'loading query',
    placeholder: 'Search expressionist-art...',
    diagnosticsEnabled: true,
    onToggleDiagnostics: () => {},
    onSubmit: () => {},
    loading: true,
  },
};

export const Focused: Story = {
  args: {
    value: '',
    placeholder: 'Search expressionist-art...',
    diagnosticsEnabled: false,
    onToggleDiagnostics: () => {},
    onSubmit: () => {},
    loading: false,
  },
  parameters: {
    docs: {
      description: {
        story: 'Border transitions to line-2, caret visible'
      }
    }
  }
};
