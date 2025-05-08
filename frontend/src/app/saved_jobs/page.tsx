'use client';

import React, { useEffect, useState } from 'react';
import JobDetailsModal from '../components/JobDetailsModal';

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
                          <div className="d-flex gap-2">
                            <button className="btn btn-sm btn-outline-primary" onClick={() => handleDetails(job)}>Details</button>
                            <button className="btn btn-sm btn-outline-danger">Unsave</button>
                            <button className="btn btn-sm btn-outline-primary">Apply</button>
                          </div>
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
