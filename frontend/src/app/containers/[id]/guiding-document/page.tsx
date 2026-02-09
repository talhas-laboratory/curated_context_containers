'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { GlassShell } from '../../../../components/glass/GlassShell';
import { GlassCard } from '../../../../components/glass/GlassCard';
import { useDescribeContainer } from '../../../../lib/hooks/use-containers';
import { useDocumentContent } from '../../../../lib/hooks/use-documents';

export default function GuidingDocumentPage() {
    const params = useParams<{ id: string }>();
    const containerId = params?.id;
    const router = useRouter();

    const {
        data: containerDetail,
        isLoading: containerLoading,
        error: containerError,
    } = useDescribeContainer(containerId || '');

    const guidingDocId = containerDetail?.container.guiding_document?.id;

    const {
        data: documentContent,
        isLoading: contentLoading,
        error: contentError,
    } = useDocumentContent(containerId, guidingDocId);

    const sidebarContent = (
        <div className="space-y-8">
            <GlassCard className="space-y-4">
                <h2 className="font-serif text-xl italic text-ink-1 break-all">
                    {containerLoading ? 'Loading…' : containerDetail?.container.name || '—'}
                </h2>
                <p className="text-sm text-ink-2 font-light">
                    {containerError ? 'Error loading container' : containerDetail?.container.theme}
                </p>

                <div className="pt-4 border-t border-line-1/50">
                    <Link
                        href={`/containers/${containerId}/search`}
                        className="flex items-center gap-2 text-sm text-ink-2 hover:text-ink-1 transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                        Back to Search
                    </Link>
                </div>
            </GlassCard>
        </div>
    );

    return (
        <GlassShell
            sidebar={sidebarContent}
            headline="Guiding Document"
        >
            <div className="max-w-4xl mx-auto pb-24 space-y-6">
                {contentLoading || containerLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 text-ink-2">
                        <div className="w-8 h-8 border-2 border-ink-2/30 border-t-ink-2 rounded-full animate-spin mb-3" />
                        <p className="animate-pulse">Loading document...</p>
                    </div>
                ) : contentError ? (
                    <div className="p-6 rounded-xl border border-ember/30 bg-ember/5 text-ember">
                        <h3 className="text-lg font-medium mb-2">Error loading document</h3>
                        <p>{contentError.message || 'Failed to load guiding document content.'}</p>
                    </div>
                ) : !guidingDocId ? (
                    <div className="p-12 text-center rounded-xl border border-line-2 bg-white/40">
                        <p className="text-ink-2 text-lg">No guiding document attached to this container.</p>
                        <Link href={`/containers/${containerId}/search`} className="mt-4 inline-block text-blue-600 hover:underline">
                            Return to search
                        </Link>
                    </div>
                ) : (
                    <GlassCard className="min-h-[60vh] p-8">
                        <div className="prose prose-slate max-w-none">
                            <pre className="whitespace-pre-wrap font-mono text-sm text-ink-1 bg-transparent border-none p-0">
                                {documentContent?.content || 'No content available.'}
                            </pre>
                        </div>
                    </GlassCard>
                )}
            </div>
        </GlassShell>
    );
}
