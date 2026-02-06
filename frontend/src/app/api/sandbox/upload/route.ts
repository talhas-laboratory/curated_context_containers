import { NextRequest } from 'next/server';
import { handleSandboxUpload } from '../../../../server/sandbox-upload';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// Back-compat route (but avoid using this path when /api/* is reverse-proxied elsewhere).
export async function POST(request: NextRequest) {
  return handleSandboxUpload(request);
}
