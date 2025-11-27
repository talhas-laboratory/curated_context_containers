import { NextRequest, NextResponse } from 'next/server';
import { S3Client, PutObjectCommand, CreateBucketCommand, HeadBucketCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// Client for uploading from the Next.js server (running on host) to MinIO (exposed on localhost)
// FORCE IPv4 127.0.0.1 to avoid Node 18+ IPv6 [::1] issues
const uploadClient = new S3Client({
  region: 'us-east-1',
  endpoint: process.env.MINIO_ENDPOINT || 'http://127.0.0.1:9000',
  credentials: {
    accessKeyId: process.env.MINIO_ACCESS_KEY || 'localminio',
    secretAccessKey: process.env.MINIO_SECRET_KEY || 'localminio123',
  },
  forcePathStyle: true, // Required for MinIO
});

// Client for generating presigned URLs for the Worker (running in Docker)
// The worker needs to access MinIO via the docker network alias 'minio'
const signingClient = new S3Client({
  region: 'us-east-1',
  endpoint: process.env.MINIO_INTERNAL_ENDPOINT || 'http://minio:9000',
  credentials: {
    accessKeyId: process.env.MINIO_ACCESS_KEY || 'localminio',
    secretAccessKey: process.env.MINIO_SECRET_KEY || 'localminio123',
  },
  forcePathStyle: true,
});

const BUCKET_NAME = 'sandbox';

async function ensureBucket() {
  try {
    await uploadClient.send(new HeadBucketCommand({ Bucket: BUCKET_NAME }));
  } catch (error) {
    try {
      console.log('Bucket not found, creating...', BUCKET_NAME);
      await uploadClient.send(new CreateBucketCommand({ Bucket: BUCKET_NAME }));
    } catch (createError) {
      // If it failed because it already exists (race condition), ignore
      console.error('Error creating bucket:', createError);
    }
  }
}

export async function POST(request: NextRequest) {
  console.log('[Upload] Request received');
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File | null;

    if (!file) {
      console.error('[Upload] No file provided');
      return NextResponse.json({ error: 'No file provided' }, { status: 400 });
    }

    console.log('[Upload] Processing file:', file.name, 'Size:', file.size);

    await ensureBucket();

    const buffer = Buffer.from(await file.arrayBuffer());
    const timestamp = Date.now();
    // Sanitize filename
    const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
    const key = `${timestamp}-${sanitizedName}`;

    // 1. Upload the file
    console.log('[Upload] Sending to MinIO...');
    await uploadClient.send(new PutObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
      Body: buffer,
      ContentType: file.type,
    }));
    console.log('[Upload] Send complete');

    // 2. Generate a pre-signed URL for the worker to download it
    // This URL must be reachable by the worker container
    const command = new GetObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
    });
    
    // Expires in 1 hour
    const presignedUrl = await getSignedUrl(signingClient, command, { expiresIn: 3600 });
    console.log('[Upload] Generated signed URL');

    return NextResponse.json({ 
      uri: presignedUrl,
      filename: file.name,
      key: key
    });

  } catch (error) {
    console.error('[Upload] Failed:', error);
    return NextResponse.json(
      { error: 'Upload failed', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
