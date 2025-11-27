'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { useJobStatus, type JobStatus } from '../lib/hooks/use-job-status';

interface UploadStatusBarProps {
  jobIds: string[];
  onComplete?: (jobId: string) => void;
  onError?: (jobId: string, error: string) => void;
}

function getStatusLabel(status: JobStatus['status']): string {
  switch (status) {
    case 'queued':
      return 'Queued for processing...';
    case 'running':
      return 'Embedding document...';
    case 'done':
      return 'Ready to search';
    case 'failed':
      return 'Upload failed';
    case 'not_found':
      return 'Job not found';
    default:
      return 'Unknown status';
  }
}

function getStatusColor(status: JobStatus['status']): string {
  switch (status) {
    case 'queued':
      return 'bg-blue-100 text-blue-600 border-blue-200';
    case 'running':
      return 'bg-purple-100 text-purple-600 border-purple-200';
    case 'done':
      return 'bg-green-100 text-green-600 border-green-200';
    case 'failed':
      return 'bg-red-100 text-red-600 border-red-200';
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200';
  }
}

function getProgress(status: JobStatus['status']): number {
  switch (status) {
    case 'queued':
      return 25;
    case 'running':
      return 60;
    case 'done':
      return 100;
    case 'failed':
      return 0;
    default:
      return 0;
  }
}

export function UploadStatusBar({ jobIds, onComplete, onError }: UploadStatusBarProps) {
  const { data, isLoading } = useJobStatus(jobIds, jobIds.length > 0);
  const notifiedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!data?.jobs) return;

    data.jobs.forEach((job) => {
      // Avoid duplicate notifications for the same job ID
      if (notifiedRef.current.has(job.job_id)) return;

      if (job.status === 'done') {
        notifiedRef.current.add(job.job_id);
        if (onComplete) onComplete(job.job_id);
      } else if (job.status === 'failed') {
        notifiedRef.current.add(job.job_id);
        if (onError) onError(job.job_id, job.error || 'Unknown error');
      }
    });
  }, [data, onComplete, onError]);

  if (!data?.jobs || data.jobs.length === 0) {
    return null;
  }

  const activeJobs = data.jobs.filter(
    (job) => job.status === 'queued' || job.status === 'running'
  );
  const completedJobs = data.jobs.filter((job) => job.status === 'done');
  const failedJobs = data.jobs.filter((job) => job.status === 'failed');

  return (
    <AnimatePresence>
      {data.jobs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed bottom-24 left-0 right-0 z-30 flex justify-center px-4 pointer-events-none"
        >
          <div className="glass-panel rounded-2xl p-4 max-w-2xl w-full shadow-glass-glow pointer-events-auto space-y-3 bg-white/80 backdrop-blur-xl border border-white/50">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-serif text-sm font-medium text-ink-1">Upload Status</h4>
              <span className="text-xs text-ink-2 font-mono">
                {completedJobs.length + failedJobs.length}/{data.jobs.length}
              </span>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
              {data.jobs.map((job) => {
                const progress = getProgress(job.status);
                const isActive = job.status === 'queued' || job.status === 'running';

                return (
                  <div
                    key={job.job_id}
                    className={`rounded-lg border p-3 transition-all ${
                      isActive ? 'bg-white/40' : 'bg-white/20'
                    } ${getStatusColor(job.status)}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {isActive && (
                          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        )}
                        {job.status === 'done' && (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        )}
                        {job.status === 'failed' && (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        )}
                        <span className="text-xs font-medium">{getStatusLabel(job.status)}</span>
                      </div>
                      <span className="text-[10px] font-mono opacity-60">
                        {job.job_id.slice(0, 8)}
                      </span>
                    </div>

                    {isActive && (
                      <div className="w-full bg-white/30 rounded-full h-1.5 overflow-hidden">
                        <motion.div
                          className="h-full bg-current rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${progress}%` }}
                          transition={{ duration: 0.5, ease: 'easeOut' }}
                        />
                      </div>
                    )}

                    {job.status === 'done' && (
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-xs mt-2 font-medium"
                      >
                        Document is ready to search!
                      </motion.p>
                    )}

                    {job.status === 'failed' && job.error && (
                      <p className="text-xs mt-2 opacity-80">{job.error}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
