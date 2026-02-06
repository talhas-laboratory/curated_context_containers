import { NextRequest } from 'next/server';
import { handleSandboxUpload } from '../../../server/sandbox-upload';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  return handleSandboxUpload(request);
}

