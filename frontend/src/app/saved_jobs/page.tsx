'use client';

import React, { useEffect, useState } from 'react';
import JobDetailsModal from '../components/JobDetailsModal';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';

interface SavedJob {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  platform: string;
  saved_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function SavedJobsPage() {
  const [jobs, setJobs] = useState<SavedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalJob, setModalJob] = useState<any | null>(null);
  const [actionLoading, setActionLoading] = useState<{[id: number]: string}>({});
  const [appliedJobs, setAppliedJobs] = useState<{[id: number]: boolean}>({});

  useEffect(() => {
    async function fetchJobs() {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/saved_jobs`);
      const data = await res.json();
      setJobs(data.saved_jobs || []);
      setLoading(false);
    }
    fetchJobs();
  }, []);

  const handleDetails = (job: SavedJob) => {
    if (modalOpen && modalJob && modalJob.id === job.id) {
      setModalOpen(false);
      setModalJob(null);
      return;
    }
    setModalJob(job);
    setModalOpen(true);
  };

  const handleUnsave = async (jobId: number) => {
    setActionLoading(a => ({ ...a, [jobId]: 'unsave' }));
    const res = await fetch(`/api/save_job/${jobId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.status === 'success') {
      setJobs(jobs => jobs.filter(j => j.id !== jobId));
    }
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  const handleApply = async (jobId: number) => {
    setActionLoading(a => ({ ...a, [jobId]: 'apply' }));
    const res = await fetch(`/api/apply_job/${jobId}`, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success' || data.status === 'already_applied') {
      setAppliedJobs(j => ({ ...j, [jobId]: true }));
    }
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <h2 className="display-5 mb-4 text-primary">Saved Jobs</h2>
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              {loading ? (
                <div>Loading...</div>
              ) : jobs.length === 0 ? (
                <div className="text-muted">No saved jobs.</div>
              ) : (
                <div className="job-list">
                  {jobs.map(job => (
                    <div className="card mb-3" key={job.id}>
                      <div className="card-body">
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <div className="flex-grow-1">
                            <h5 className="card-title mb-1">
                              <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-decoration-none">{job.title}</a>
                            </h5>
                            <h6 className="card-subtitle mb-2 text-muted">{job.company}</h6>
                            <div className="d-flex align-items-center text-muted mb-2">
                              <small className="me-3"><i className="bi bi-geo-alt"></i> {job.location}</small>
                              <small className="me-3"><i className="bi bi-calendar"></i> Saved on {job.saved_at}</small>
                              <small><i className="bi bi-globe"></i> {job.platform}</small>
                            </div>
                          </div>
                          <Stack direction="row" spacing={1}>
                            <Button size="small" variant="outlined" onClick={() => handleDetails(job)}>
                              Details
                            </Button>
                            <Button size="small" variant="outlined" color="error" onClick={() => handleUnsave(job.id)} disabled={actionLoading[job.id] === 'unsave'}>
                              {actionLoading[job.id] === 'unsave' ? 'Unsaving...' : 'Unsave'}
                            </Button>
                            <Button size="small" variant="outlined" color="primary" onClick={() => handleApply(job.id)} disabled={actionLoading[job.id] === 'apply' || appliedJobs[job.id]}>
                              {appliedJobs[job.id] ? 'Applied' : actionLoading[job.id] === 'apply' ? 'Applying...' : 'Apply'}
                            </Button>
                          </Stack>
                        </div>
                        {/* No description here, only in modal */}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <JobDetailsModal open={modalOpen} onClose={() => { setModalOpen(false); setModalJob(null); }} job={modalJob} />
    </div>
  );
}
