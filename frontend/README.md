# Local Latent Containers — Frontend

Next.js frontend for Local Latent Containers, providing a clean UI for browsing containers and searching with hybrid retrieval.

## Prerequisites

- Node.js 18+ and npm/pnpm
- MCP server running on `http://localhost:7801` (or configure `NEXT_PUBLIC_MCP_BASE_URL`)
- Bearer token for MCP API (see Configuration)

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   # or
   pnpm install
   ```

2. Configure environment (see `.env.example`):
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your MCP token
   ```

3. Run development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000)

## Configuration

### Environment Variables

- `NEXT_PUBLIC_MCP_BASE_URL` — MCP server URL (default: `http://localhost:7801`)
- `NEXT_PUBLIC_MCP_TOKEN` — Bearer token for MCP API (optional, can also use localStorage)

### Token Storage

The app checks for tokens in this order:
1. `NEXT_PUBLIC_MCP_TOKEN` environment variable
2. `localStorage` key `llc_mcp_token`

You can set the token programmatically:
```typescript
import { setToken } from '@/lib/mcp-client';
setToken('your-token-here');
```

## Features

- **Container Gallery** (`/containers`) — Browse all containers with filters
- **Search Workspace** (`/containers/[id]/search`) — Search within a container with diagnostics; modes include semantic, hybrid, bm25, crossmodal, graph, hybrid_graph
- **Document Modal** — View full document details with provenance
- **Keyboard Navigation** — `/` to focus search, `Esc` to clear/close
- **Accessibility** — WCAG AA compliant, full keyboard support, reduced-motion support
- **Diagnostics** — Toggle diagnostics panel to see search timings and stage scores

## Keyboard Shortcuts

- `/` — Focus search input
- `Esc` — Clear search query or close modal
- `Enter` — Submit search
- `Tab` — Navigate between interactive elements

## Development

### Scripts

- `npm run dev` — Start development server
- `npm run build` — Build for production
- `npm run start` — Start production server
- `npm run lint` — Run ESLint
- `npm run storybook` — Start Storybook
- `npm test` — Run tests (placeholder, see TECHNICAL_DEBT.md)

### Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js app router pages
│   │   ├── containers/   # Container gallery and search routes
│   │   └── page.tsx      # Home (redirects to first container)
│   ├── components/       # React components
│   │   ├── ContainerCard.tsx
│   │   ├── DiagnosticsRail.tsx
│   │   ├── DocumentModal.tsx
│   │   ├── ResultItem.tsx
│   │   └── SearchInput.tsx
│   ├── lib/              # Utilities and hooks
│   │   ├── hooks/        # React Query hooks
│   │   ├── mcp-client.ts # MCP API client
│   │   ├── query-client.ts
│   │   └── types.ts      # Shared TypeScript types
│   └── stories/          # Storybook stories
└── public/               # Static assets
```

## Testing

Tests are not yet configured. See `single_source_of_truth/work/TECHNICAL_DEBT.md` for details.

## Design System

The UI follows the minimalist design system defined in `single_source_of_truth/design/`:
- Monochrome chrome with IKB blue reserved for data
- 4px grid spacing system
- Motion tokens (120–320ms transitions)
- WCAG AA accessibility standards

## Troubleshooting

### CORS Errors

Ensure the MCP server allows requests from `http://localhost:3000` (or your frontend URL).

### Authentication Errors

Check that your bearer token is correctly set in environment variables or localStorage.

### Search Not Working

1. Verify MCP server is running: `curl http://localhost:7801/healthz`
2. Check browser console for errors
3. Verify token is set: Check Network tab for `Authorization` header

## License

See root LICENSE file.
