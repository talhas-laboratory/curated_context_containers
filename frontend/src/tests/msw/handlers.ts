import { http, HttpResponse } from 'msw';

const containers = [
  {
    id: 'container-1',
    name: 'Expressionist Art',
    theme: 'art',
    modalities: ['text'],
    state: 'active',
    stats: {
      document_count: 3,
      chunk_count: 9,
    },
  },
];

const containerDetail = {
  ...containers[0],
  description: 'Expressionist movement documents',
  embedder: 'gemma3',
  embedder_version: 'v1',
  dims: 768,
};

const initialDocuments = [
  {
    id: 'doc-1',
    uri: 'https://example.com/doc.pdf',
    title: 'History of Expressionism',
    mime: 'application/pdf',
    hash: 'hash',
    state: 'active',
    chunk_count: 3,
    meta: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

let documents = [...initialDocuments];
let jobStatusFixture: Record<string, { status: 'queued' | 'running' | 'done' | 'failed' | 'not_found'; error?: string | null }> = {};

export function resetDocumentFixtures() {
  documents = [...initialDocuments];
}

export function resetJobFixtures() {
  jobStatusFixture = {
    'job-refresh-1': { status: 'running' },
    'job-export-1': { status: 'done' },
  };
}

resetJobFixtures();

export const handlers = [
  http.post('*/v1/containers/create', async ({ request }) => {
    const body = await request.json();
    if (!body.name) {
      return new HttpResponse(JSON.stringify({ error: { code: 'VALIDATION_ERROR', message: 'name required' } }), {
        status: 400,
      });
    }

    return HttpResponse.json({
      version: 'v1',
      request_id: 'req-create',
      success: true,
      container_id: body.name,
      message: `Container '${body.name}' created successfully`,
    });
  }),

  http.post('*/v1/containers/list', async ({ request }) => {
    const body = await request.json();
    if (body.state === 'empty') {
      return HttpResponse.json({ containers: [], total: 0 });
    }
    if (body.state === 'error') {
      return new HttpResponse(JSON.stringify({ error: { code: 'SERVER_ERROR', message: 'fail' } }), {
        status: 500,
      });
    }
    return HttpResponse.json({ containers, total: containers.length });
  }),

  http.post('*/v1/containers/describe', async ({ request }) => {
    const body = await request.json();
    if (body.container === 'missing') {
      return new HttpResponse(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'not found' } }), {
        status: 404,
      });
    }
    return HttpResponse.json({ container: containerDetail, request_id: 'req-123', issues: [] });
  }),

  http.post('*/v1/documents/list', async ({ request }) => {
    const body = await request.json();
    if (body.container === 'missing') {
      return new HttpResponse(JSON.stringify({ error: { code: 'CONTAINER_NOT_FOUND', message: 'missing' } }), {
        status: 404,
      });
    }
    return HttpResponse.json({
      container_id: body.container,
      documents,
      total: documents.length,
      request_id: 'req-docs',
    });
  }),

  http.post('*/v1/documents/delete', async ({ request }) => {
    const body = await request.json();
    const index = documents.findIndex((doc) => doc.id === body.document_id);
    if (index === -1) {
      return new HttpResponse(JSON.stringify({ error: { code: 'DOCUMENT_NOT_FOUND', message: 'missing' } }), {
        status: 404,
      });
    }
    documents.splice(index, 1);
    return HttpResponse.json({
      document_id: body.document_id,
      deleted: true,
      request_id: 'req-del',
    });
  }),

  http.post('*/v1/search', async ({ request }) => {
    const body = await request.json();
    const query = (body.query as string) || 'image-query';
    const isGraphRequest = body.mode === 'graph' || body.mode === 'hybrid_graph' || !!body.graph;

    if (query === 'error') {
      return new HttpResponse(JSON.stringify({ error: { code: 'NO_HITS', message: 'nothing' } }), { status: 400 });
    }

    if (query === 'empty') {
      return HttpResponse.json({
        version: 'v1',
        request_id: 'req-empty',
        query,
        results: [],
        total_hits: 0,
        returned: 0,
        diagnostics: {
          mode: body.mode ?? 'hybrid',
          bm25_hits: 0,
          vector_hits: 0,
          latency_budget_ms: 900,
          latency_over_budget_ms: 0,
        },
        timings_ms: { total_ms: 120 },
        issues: ['NO_HITS'],
      });
    }

    const response = {
      version: 'v1',
      request_id: 'req-456',
      query,
      results: [
        {
          chunk_id: 'chunk-1',
          doc_id: 'doc-1',
          container_id: 'container-1',
          container_name: 'Expressionist Art',
          title: 'History of Expressionism',
          snippet: 'Expressionism is a modernist movement...',
          uri: 's3://bucket/doc-1',
          score: 0.92,
          modality: 'text',
          provenance: { source: 'wiki', ingested_at: '2024-01-01T00:00:00Z' },
          meta: { tags: ['art'] },
        },
      ],
      total_hits: 1,
      returned: 1,
      diagnostics: {
        mode: body.mode ?? 'hybrid',
        bm25_hits: 1,
        vector_hits: 1,
        latency_budget_ms: 900,
        latency_over_budget_ms: 0,
      },
      timings_ms: {
        total_ms: 150,
        vector_ms: 80,
        bm25_ms: 40,
        fuse_ms: 30,
      },
      issues: [],
    };

    if (isGraphRequest) {
      response.graph_context = {
        nodes: [{ id: 'node-1', label: 'GraphOS', type: 'Project', summary: 'Platform', source_chunk_ids: ['chunk-1'] }],
        edges: [{ source: 'Team', target: 'GraphOS', type: 'WORKS_ON', source_chunk_ids: ['chunk-2'] }],
        snippets: [
          { chunk_id: 'chunk-1', doc_id: 'doc-1', title: 'Decision doc', text: 'Context', uri: 'doc://1' },
          { chunk_id: 'chunk-2', doc_id: 'doc-2', title: 'Team note', text: 'Relation', uri: 'doc://2' },
        ],
      };
      response.diagnostics = { ...response.diagnostics, graph_hits: 2 };
      response.timings_ms = { ...response.timings_ms, graph_ms: 12 };
    }

    return HttpResponse.json(response);
  }),

  http.post('*/v1/containers/graph_search', async ({ request }) => {
    const body = await request.json();
    const mode = body.mode || 'nl';
    if (body.query === 'bad-cypher' && mode === 'cypher') {
      return new HttpResponse(JSON.stringify({ error: { code: 'GRAPH_QUERY_INVALID', message: 'bad query' } }), {
        status: 400,
      });
    }
    return HttpResponse.json({
      version: 'v1',
      request_id: 'req-graph',
      nodes: [
        { id: 'node-1', label: 'GraphOS', type: 'Project', summary: 'Platform', source_chunk_ids: ['chunk-1'] },
      ],
      edges: [{ source: 'Team', target: 'GraphOS', type: 'WORKS_ON', source_chunk_ids: ['chunk-2'] }],
      snippets: [
        { chunk_id: 'chunk-1', doc_id: 'doc-1', title: 'Decision doc', text: 'Context', uri: 'doc://1' },
        { chunk_id: 'chunk-2', doc_id: 'doc-2', title: 'Team note', text: 'Relation', uri: 'doc://2' },
      ],
      diagnostics: { mode, graph_hits: 1 },
      timings_ms: { graph_ms: 12 },
      issues: [],
    });
  }),

  http.post('*/v1/admin/refresh', async () => {
    const jobId = 'job-refresh-1';
    jobStatusFixture[jobId] = { status: 'running' };
    return HttpResponse.json({
      version: 'v1',
      request_id: 'req-refresh',
      job_id: jobId,
      status: 'queued',
      timings_ms: { db_query: 5 },
      issues: [],
    });
  }),

  http.post('*/v1/admin/export', async () => {
    const jobId = 'job-export-1';
    jobStatusFixture[jobId] = { status: 'done' };
    return HttpResponse.json({
      version: 'v1',
      request_id: 'req-export',
      job_id: jobId,
      status: 'queued',
      timings_ms: { db_query: 4 },
      issues: [],
    });
  }),

  http.post('*/v1/jobs/status', async ({ request }) => {
    const body = await request.json();
    const jobIds: string[] = body.job_ids || [];

    return HttpResponse.json({
      jobs: jobIds.map((jobId) => {
        const entry = jobStatusFixture[jobId];
        return {
          job_id: jobId,
          status: entry?.status ?? 'not_found',
          error: entry?.error ?? null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
      }),
    });
  }),
];
