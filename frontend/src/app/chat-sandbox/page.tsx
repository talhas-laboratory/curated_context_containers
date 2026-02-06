'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import { GlassShell } from '../../components/glass/GlassShell';
import { GlassCard } from '../../components/glass/GlassCard';
import { GlassInput } from '../../components/glass/GlassInput';
import { UploadStatusBar } from '../../components/UploadStatusBar';
import { useAddToContainer } from '../../lib/hooks/use-add-to-container';
import { useListContainers } from '../../lib/hooks/use-containers';
import { useSearch } from '../../lib/hooks/use-search';
import { createId } from '../../lib/ids';
import type { JobSummary, SearchResult } from '../../lib/types';

interface Message {
  id: string;
  role: 'user' | 'system';
  content?: string;
  results?: SearchResult[];
  timestamp: number;
}

export default function ChatSandboxPage() {
  const [activeContainerId, setActiveContainerId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);
  const [completedJobIds, setCompletedJobIds] = useState<Set<string>>(new Set());
  const [isUploading, setIsUploading] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragDepth = useRef(0);

  const { data: containerData } = useListContainers('active');
  const searchMutation = useSearch();
  const addToContainerMutation = useAddToContainer();

  useEffect(() => {
    if (containerData?.containers.length && !activeContainerId) {
      // Prefer a PDF-capable container since this page only uploads PDFs.
      const pdfCapable = containerData.containers.find((c) => c.modalities?.includes('pdf'));
      setActiveContainerId(pdfCapable?.id || containerData.containers[0].id);
    }
  }, [containerData, activeContainerId]);

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !activeContainerId) return;

    const userMsg: Message = {
      id: createId(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    try {
      const response = await searchMutation.mutateAsync({
        query: userMsg.content!,
        containerIds: [activeContainerId],
        mode: 'hybrid',
        k: 5,
        diagnostics: true,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          results: response.results,
          timestamp: Date.now(),
        },
      ]);
    } catch (error) {
      console.error('Search failed:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: 'Search failed. Check console logs.',
          timestamp: Date.now(),
        },
      ]);
    }
  };

  const isPdfFile = (file: File) => {
    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  };

  const uploadFile = async (file: File, containerId: string) => {
    console.log('Uploading file...', file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Avoid /api/* because many deployments reverse-proxy /api/* to the MCP backend.
      const uploadRes = await fetch('/sandbox/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        const err = await uploadRes.json().catch(() => ({ error: uploadRes.statusText }));
        throw new Error(err.error || 'Upload failed');
      }

      const { uri } = await uploadRes.json();
      console.log('Upload complete, URI:', uri);

      const response = await addToContainerMutation.mutateAsync({
        containerId,
        sources: [
          {
            uri,
            title: file.name,
            modality: 'pdf',
            mime: file.type,
          },
        ],
        mode: 'async',
      });

      if (response.jobs?.length) {
        const newJobs = response.jobs;
        setJobs((prev) => [...newJobs, ...prev].slice(0, 6));
        // Track job IDs for status polling
        const newJobIds = newJobs.map((j) => j.job_id);
        setActiveJobIds((prev) => [...prev, ...newJobIds]);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: `Queued "${file.name}".`,
          timestamp: Date.now(),
        },
      ]);
    } catch (error) {
      console.error('Upload flow failed:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: `Upload failed: ${(error as Error).message}.`,
          timestamp: Date.now(),
        },
      ]);
    }
  };

  const handleFiles = async (files: File[]) => {
    if (!activeContainerId) {
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: 'Select a container before uploading documents.',
          timestamp: Date.now(),
        },
      ]);
      return;
    }

    const selectedContainer = containerData?.containers.find((c) => c.id === activeContainerId);
    const supportsPdf = !!selectedContainer && selectedContainer.modalities?.includes('pdf');

    const containerId = activeContainerId;
    const pdfFiles = files.filter(isPdfFile);
    const rejectedFiles = files.filter((file) => !isPdfFile(file));

    if (rejectedFiles.length) {
      const names = rejectedFiles.map((file) => `"${file.name}"`).join(', ');
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: `Skipped non-PDF file(s): ${names}.`,
          timestamp: Date.now(),
        },
      ]);
    }

    if (!pdfFiles.length) return;

    if (!supportsPdf) {
      const modalities = selectedContainer?.modalities?.length ? selectedContainer.modalities.join(', ') : 'unknown';
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'system',
          content: `Upload failed: this container doesn't accept PDFs (modalities: ${modalities}). Select a PDF-enabled container.`,
          timestamp: Date.now(),
        },
      ]);
      return;
    }

    setIsUploading(true);
    try {
      for (const file of pdfFiles) {
        await uploadFile(file, containerId);
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (!files.length) return;
    await handleFiles(files);
  };

  const isFileDrag = (event: React.DragEvent) => {
    return Array.from(event.dataTransfer.types).includes('Files');
  };

  const handleDragEnter = (event: React.DragEvent) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    dragDepth.current += 1;
    setIsDragActive(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) {
      setIsDragActive(false);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    const selectedContainer = containerData?.containers.find((c) => c.id === activeContainerId);
    const supportsPdf = !!selectedContainer && selectedContainer.modalities?.includes('pdf');
    event.dataTransfer.dropEffect = supportsPdf ? 'copy' : 'none';
  };

  const handleDrop = (event: React.DragEvent) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    dragDepth.current = 0;
    setIsDragActive(false);
    const files = Array.from(event.dataTransfer.files || []);
    if (files.length) {
      void handleFiles(files);
    }
  };

  const activeContainer = containerData?.containers.find((c) => c.id === activeContainerId);
  const activeContainerSupportsPdf = !!activeContainer && activeContainer.modalities?.includes('pdf');

  const sidebarContent = (
    <div className="space-y-8">
      <GlassCard className="space-y-4">
        <h3 className="font-serif text-lg italic text-ink-1">Containers</h3>
        <div className="space-y-2">
          {containerData?.containers.map((container) => (
            <button
              key={container.id}
              onClick={() => setActiveContainerId(container.id)}
              className={`w-full rounded-xl px-4 py-3 text-left transition-all duration-300 ${
                container.id === activeContainerId
                  ? 'bg-white/60 shadow-glass border border-white/50 text-ink-1'
                  : 'text-ink-2 hover:bg-white/30 hover:text-ink-1'
              }`}
            >
              <p className="text-sm font-medium">{container.name}</p>
              <p className="text-xs text-ink-2 opacity-70">{container.theme}</p>
            </button>
          ))}
          {containerData && containerData.containers.length === 0 && (
            <p className="text-sm text-ink-2 px-2">No containers available.</p>
          )}
        </div>
      </GlassCard>

      <GlassCard className="space-y-4">
        <h3 className="font-serif text-lg italic text-ink-1">Ingestion Queue</h3>
        <ul className="space-y-3">
          <AnimatePresence initial={false}>
            {jobs.map((job) => (
              <motion.li
                key={job.job_id}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center justify-between text-sm text-ink-2 bg-white/30 rounded-lg p-2 border border-white/20"
              >
                <span className="font-mono text-xs text-ink-2/80">{job.job_id.slice(0, 8)}</span>
                <span className="text-[10px] uppercase tracking-wider font-medium px-2 py-0.5 bg-white/50 rounded-full border border-white/40">
                  {job.status}
                </span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      </GlassCard>
    </div>
  );

  return (
    <GlassShell
      sidebar={sidebarContent}
      headline="Chat Sandbox"
      description="Upload PDFs into a container, then ask calm, deterministic questions."
    >
      <div
        className="flex flex-col min-h-[600px] relative"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isDragActive && (
          <div className="absolute inset-0 z-30 flex items-center justify-center rounded-3xl bg-white/60 backdrop-blur-sm border border-white/70 pointer-events-none">
            <div className="text-center">
              <p className="text-sm font-medium uppercase tracking-widest text-ink-2/70">
                {!activeContainerId
                  ? 'Select a container to upload'
                  : activeContainerSupportsPdf
                    ? 'Drop PDFs to upload'
                    : "This container doesn't accept PDFs"}
              </p>
              <p className="text-xs text-ink-2/60 mt-2">PDF only for now.</p>
            </div>
          </div>
        )}
        {/* Context Indicator */}
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }}
          className="absolute top-0 right-0 left-0 flex justify-center -mt-8 pointer-events-none"
        >
           <span className="text-xs font-medium tracking-widest uppercase text-ink-2/50 bg-white/30 backdrop-blur-sm px-3 py-1 rounded-full border border-white/20">
             {activeContainer ? activeContainer.name : 'Select container'}
           </span>
        </motion.div>

        {/* Chat Stream */}
        <section className="flex-1 space-y-8 pb-32 min-h-[400px]" aria-live="polite">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center p-12">
              <GlassCard className="text-center max-w-md mx-auto border-dashed border-white/40 bg-white/10">
                <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-blue-100 to-purple-100 mx-auto mb-4 blur-xl opacity-60"></div>
                <p className="text-sm text-ink-2/70">Select a container and upload a PDF to start.</p>
              </GlassCard>
            </div>
          )}

          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                className={`flex flex-col gap-3 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                {msg.role === 'user' ? (
                  <div className="max-w-2xl rounded-2xl rounded-tr-sm bg-gradient-to-br from-white/90 to-white/60 backdrop-blur-md border border-white/60 shadow-glass px-6 py-4 text-ink-1">
                    <p className="font-serif text-lg leading-relaxed">{msg.content}</p>
                  </div>
                ) : (
                  <div className="w-full max-w-4xl space-y-6">
                    {msg.content && (
                      <GlassCard className="bg-white/40 border-white/30">
                         <p className="text-sm text-ink-2">{msg.content}</p>
                      </GlassCard>
                    )}
                    {msg.results && (
                      <div className="grid gap-4 sm:grid-cols-2">
                        {msg.results.map((res, i) => (
                          <motion.div
                            key={res.chunk_id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                          >
                            <GlassCard className="h-full group hover:bg-white/70 transition-colors">
                              <div className="mb-3 flex items-start justify-between gap-3">
                                <div>
                                  <h4 className="font-serif text-base font-medium text-ink-1 leading-tight mb-1">
                                    {res.title || 'Untitled Document'}
                                  </h4>
                                  <p className="text-xs text-ink-2 opacity-60 font-mono">{res.container_name}</p>
                                </div>
                                {typeof res.score === 'number' && (
                                  <span className={`
                                    text-[10px] font-bold px-2 py-1 rounded-full border
                                    ${res.score > 0.8 ? 'bg-blue-50 text-blue-600 border-blue-100' : 'bg-gray-50 text-gray-500 border-gray-100'}
                                  `}>
                                    {(res.score * 100).toFixed(0)}%
                                  </span>
                                )}
                              </div>
                              
                              <div className="relative">
                                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-400/30 to-transparent rounded-full"></div>
                                <p className="pl-3 text-sm text-ink-2 leading-relaxed line-clamp-4 group-hover:text-ink-1 transition-colors">
                                  {res.snippet}
                                </p>
                              </div>

                              <div className="mt-4 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider text-ink-2/50">
                                {res.modality && <span>{res.modality}</span>}
                                {res.provenance?.ingested_at && (
                                  <>
                                    <span>•</span>
                                    <span>{new Date(res.provenance.ingested_at as string).toLocaleDateString()}</span>
                                  </>
                                )}
                              </div>
                            </GlassCard>
                          </motion.div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={scrollRef} />
        </section>

        {/* Floating Command Bar */}
        <div className="sticky bottom-6 left-0 right-0 flex justify-center z-20 px-4">
          <GlassCard className="w-full max-w-3xl !p-2 !rounded-full flex items-center gap-2 shadow-glass-glow bg-white/70 backdrop-blur-xl border-white/50">
             <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || !activeContainerId || !activeContainerSupportsPdf}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-white/50 hover:bg-white text-ink-2 hover:text-ink-1 transition-all disabled:opacity-40 group relative"
                title="Upload PDF"
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  className="hidden" 
                  accept=".pdf" 
                  onChange={handleFileUpload} 
                  autoComplete="off"
                  data-lpignore="true"
                />
                {isUploading ? (
                  <div className="w-4 h-4 border-2 border-ink-2 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" x2="12" y1="3" y2="15" />
                  </svg>
                )}
              </button>

              <form 
                className="flex-1 flex items-center"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
              >
                <input
                  className="w-full bg-transparent border-none focus:ring-0 px-2 text-ink-1 placeholder:text-ink-2/60 font-light text-lg"
                  placeholder={activeContainerId ? "Ask a question..." : "Select a container first"}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={!activeContainerId}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || !activeContainerId}
                  className="mr-1 px-6 py-2 rounded-full bg-ink-1 text-white text-sm font-medium hover:bg-ink-1/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ink-1/20"
                >
                  Send
                </button>
              </form>
          </GlassCard>
        </div>
      </div>

      {/* Upload Status Bar */}
      <UploadStatusBar
        jobIds={activeJobIds.filter((id) => !completedJobIds.has(id))}
        onComplete={(jobId) => {
          setCompletedJobIds((prev) => new Set([...prev, jobId]));
          setActiveJobIds((prev) => prev.filter((id) => id !== jobId));
        }}
        onError={(jobId, error) => {
          setCompletedJobIds((prev) => new Set([...prev, jobId]));
          setActiveJobIds((prev) => prev.filter((id) => id !== jobId));
        }}
      />
    </GlassShell>
  );
}
