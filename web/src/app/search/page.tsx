'use client';

import React, { useState } from 'react';
import JobDetailsModal from '../components/JobDetailsModal';
import Pagination from '@mui/material/Pagination';
import Stack from '@mui/material/Stack';

interface Suggestion {
  category: string;
  suggestion: string;
  action_items: string[];
}

interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  platform: string;
  application_status?: string;
  requirements?: string[];
  suggestions?: Suggestion[];
}

const COMMON_LOCATIONS = [
  // North America
  'United States', 'Canada', 'Mexico',
  
  // Europe
  'United Kingdom', 'Germany', 'France', 'Netherlands', 'Spain', 'Italy',
  'Switzerland', 'Sweden', 'Denmark', 'Norway', 'Finland', 'Ireland',
  'Belgium', 'Austria', 'Poland', 'Portugal', 'Greece', 'Czech Republic',
  
  // Asia
  'India', 'China', 'Japan', 'South Korea', 'Singapore', 'Hong Kong',
  'Malaysia', 'Thailand', 'Vietnam', 'Indonesia', 'Philippines',
  
  // Middle East
  'UAE', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Bahrain', 'Oman',
  
  // Africa
  'South Africa', 'Egypt', 'Nigeria', 'Kenya', 'Morocco',
  
  // South America
  'Brazil', 'Argentina', 'Chile', 'Colombia', 'Peru',
  
  // Oceania
  'Australia', 'New Zealand',
  
  // Remote Options
  'Remote', 'Work from Home', 'Anywhere'
];

export default function SearchPage() {
  const [keyword, setKeyword] = useState('');
  const [location, setLocation] = useState('');
  const [platform, setPlatform] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<{[id: number]: string}>({});
  const [actionMsg, setActionMsg] = useState<{[id: number]: string}>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [modalJob, setModalJob] = useState<Job | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const handleSearch = async (e?: React.FormEvent, pageOverride?: number) => {
    if (e) e.preventDefault();
    setLoading(true);
    const params = new URLSearchParams({ keyword, location, platform, page: String(pageOverride || page) });
    const res = await fetch(`/api/jobs?${params.toString()}`);
    const data = await res.json();
    setJobs(data.jobs || []);
    setTotalPages(data.pages || 1);
    setLoading(false);
  };

  const handlePageChange = (_: unknown, value: number) => {
    setPage(value);
    handleSearch(undefined, value);
  };

  const handleDetails = async (jobId: number) => {
    if (modalOpen && modalJob && modalJob.id === jobId) {
      setModalOpen(false);
      setModalJob(null);
      return;
    }
    setModalOpen(true);
    setModalJob(null);
    setActionLoading(a => ({ ...a, [jobId]: 'details' }));
    const res = await fetch(`/api/job_details/${jobId}`);
    const data = await res.json();
    setModalJob(data);
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  const handleSave = async (jobId: number) => {
    setActionLoading(a => ({ ...a, [jobId]: 'save' }));
    const res = await fetch(`/api/save_job/${jobId}`, { method: 'POST' });
    const data = await res.json();
    setActionMsg(m => ({ ...m, [jobId]: data.status === 'success' ? 'Saved!' : data.status === 'already_saved' ? 'Already saved.' : 'Error saving.' }));
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  const handleApply = async (jobId: number) => {
    setActionLoading(a => ({ ...a, [jobId]: 'apply' }));
    const res = await fetch(`/api/apply_job/${jobId}`, { method: 'POST' });
    const data = await res.json();
    setActionMsg(m => ({ ...m, [jobId]: data.status === 'success' ? 'Applied!' : data.status === 'already_applied' ? 'Already applied.' : 'Error applying.' }));
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <h2 className="display-5 mb-4 text-primary">Job Search</h2>
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              <form className="row g-3" onSubmit={handleSearch}>
                <div className="col-md-5">
                  <div className="input-group">
                    <span className="input-group-text bg-primary text-white">
                      <i className="bi bi-search"></i>
                    </span>
                    <input
                      name="keyword"
                      placeholder="Role (e.g., Software Engineer, Product Manager)"
                      value={keyword}
                      onChange={e => setKeyword(e.target.value)}
                      className="form-control form-control-lg"
                    />
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="input-group">
                    <span className="input-group-text bg-primary text-white">
                      <i className="bi bi-geo-alt"></i>
                    </span>
                    <select
                      name="location"
                      value={location}
                      onChange={e => setLocation(e.target.value)}
                      className="form-select form-select-lg"
                    >
                      <option value="">Select Location</option>
                      {COMMON_LOCATIONS.map((loc) => (
                        <option key={loc} value={loc}>
                          {loc}
                        </option>
                      ))}
                    </select>
                    {location && (
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={() => setLocation('')}
                      >
                        <i className="bi bi-x"></i>
                      </button>
                    )}
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="input-group">
                    <span className="input-group-text bg-primary text-white">
                      <i className="bi bi-globe"></i>
                    </span>
                    <select
                      name="platform"
                      value={platform}
                      onChange={e => setPlatform(e.target.value)}
                      className="form-select form-select-lg"
                    >
                      <option value="">All Platforms</option>
                      <option value="LinkedIn">LinkedIn</option>
                      <option value="Indeed">Indeed</option>
                      <option value="ZipRecruiter">ZipRecruiter</option>
                    </select>
                    {platform && (
                      <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={() => setPlatform('')}
                      >
                        <i className="bi bi-x"></i>
                      </button>
                    )}
                  </div>
                </div>
                <div className="col-md-1">
                  <button className="btn btn-primary btn-lg w-100" type="submit" disabled={loading}>
                    <i className="bi bi-search"></i>
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
      <div className="row">
        <div className="col-12">
          <div className="job-list">
            {loading && <div className="text-center">Loading...</div>}
            {!loading && jobs.length === 0 && <div className="text-center text-muted">No jobs found.</div>}
            {jobs.map(job => (
              <div className="card mb-3" key={job.id}>
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <h5 className="card-title mb-0">
                      <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-decoration-none">
                        {job.title}
                        {job.application_status === 'Applied' && (
                          <i className="bi bi-check-circle-fill text-success ms-2" title="Applied"></i>
                        )}
                      </a>
                    </h5>
                    <div className="d-flex gap-2">
                      <button className="btn btn-sm btn-outline-primary" disabled={actionLoading[job.id] === 'details'} onClick={() => handleDetails(job.id)}>
                        Details
                      </button>
                      <button className="btn btn-sm btn-outline-success" disabled={actionLoading[job.id] === 'save'} onClick={() => handleSave(job.id)}>
                        Save
                      </button>
                      {job.application_status === 'Applied' ? (
                        <button className="btn btn-sm btn-outline-danger" disabled>
                          Didn&apos;t Apply
                        </button>
                      ) : (
                        <button className="btn btn-sm btn-outline-primary" disabled={actionLoading[job.id] === 'apply'} onClick={() => handleApply(job.id)}>
                          Apply
                        </button>
                      )}
                    </div>
                  </div>
                  <h6 className="card-subtitle mb-2 text-muted">{job.company}</h6>
                  <div className="d-flex align-items-center text-muted mb-2">
                    <small className="me-3"><i className="bi bi-geo-alt"></i> {job.location}</small>
                    <small><i className="bi bi-globe"></i> {job.platform}</small>
                  </div>
                  {actionMsg[job.id] && <div className="alert alert-info mt-2 py-1 px-2">{actionMsg[job.id]}</div>}
                </div>
              </div>
            ))}
          </div>
          <Stack direction="row" justifyContent="center" sx={{ mt: 3 }}>
            <Pagination count={totalPages} page={page} onChange={handlePageChange} color="primary" />
          </Stack>
        </div>
      </div>
      <JobDetailsModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setModalJob(null); }}
        job={modalJob ? { ...modalJob, requirements: modalJob.requirements ?? [], suggestions: modalJob.suggestions ?? [] } : null}
      />
    </div>
  );
}
