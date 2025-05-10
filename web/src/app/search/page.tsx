'use client';

import React, { useState, useEffect } from 'react';
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
  date_posted: string;
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

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
  const [locations, setLocations] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [sortBy, setSortBy] = useState('date_posted');
  const [sortOrder, setSortOrder] = useState('desc');
  const [searchParams, setSearchParams] = useState({
    keyword: '',
    location: '',
    platform: ''
  });
  const [error, setError] = useState<string | null>(null);
  const [jobStatuses, setJobStatuses] = useState<{[id: number]: string}>({});

  // Restore search state from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('jobSearchState');
    if (saved) {
      const { keyword, location, platform, jobs, page, sortBy, sortOrder } = JSON.parse(saved);
      setKeyword(keyword);
      setLocation(location);
      setPlatform(platform);
      setJobs(jobs);
      setPage(page);
      setSortBy(sortBy);
      setSortOrder(sortOrder);
    }
  }, []);

  // Fetch applied jobs and merge statuses into job list
  useEffect(() => {
    async function fetchAppliedStatuses() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/tracker`);
        const data = await res.json();
        const appliedStatuses: {[id: number]: string} = {};
        (data.applications || []).forEach((app: any) => {
          appliedStatuses[app.job_id] = app.status;
        });
        setJobStatuses(s => ({ ...s, ...appliedStatuses }));
      } catch {}
    }
    if (jobs.length > 0) fetchAppliedStatuses();
  }, [jobs]);

  // Save search state to localStorage whenever jobs or params change
  useEffect(() => {
    localStorage.setItem('jobSearchState', JSON.stringify({
      keyword, location, platform, jobs, page, sortBy, sortOrder
    }));
  }, [keyword, location, platform, jobs, page, sortBy, sortOrder]);

  // Add effect to sync job status updates from localStorage
  useEffect(() => {
    function syncJobStatusUpdates() {
      const updates = JSON.parse(localStorage.getItem('jobStatusUpdates') || '{}');
      if (Object.keys(updates).length > 0) {
        setJobStatuses(s => ({ ...s, ...updates }));
        setJobs(jobs => jobs.map(j => updates[j.id] ? { ...j, application_status: updates[j.id] } : j));
        localStorage.removeItem('jobStatusUpdates');
      }
    }
    syncJobStatusUpdates();
    window.addEventListener('focus', syncJobStatusUpdates);
    return () => window.removeEventListener('focus', syncJobStatusUpdates);
  }, []);

  const handleSearch = async (e?: React.FormEvent, pageOverride?: number) => {
    if (e) e.preventDefault();
    setLoading(true);
    const params = new URLSearchParams({
      keyword,
      location,
      platform,
      page: String(pageOverride || page),
      sort_by: sortBy,
      sort_order: sortOrder
    });
    const res = await fetch(`${API_BASE_URL}/api/search?${params.toString()}`);
    const data = await res.json();
    setJobs(data.jobs || []);
    setTotalPages(data.pages || 1);
    setLoading(false);
    // After search, fetch applied statuses
    try {
      const res2 = await fetch(`${API_BASE_URL}/api/tracker`);
      const tracker = await res2.json();
      const appliedStatuses: {[id: number]: string} = {};
      (tracker.applications || []).forEach((app: any) => {
        appliedStatuses[app.job_id] = app.status;
      });
      setJobStatuses(s => ({ ...s, ...appliedStatuses }));
    } catch {}
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
    const res = await fetch(`${API_BASE_URL}/api/job_details/${jobId}`);
    const data = await res.json();
    setModalJob(data);
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  const handleSave = async (jobId: number) => {
    setActionLoading(a => ({ ...a, [jobId]: 'save' }));
    const res = await fetch(`${API_BASE_URL}/api/save_job/${jobId}`, { method: 'POST' });
    const data = await res.json();
    setActionMsg(m => ({ ...m, [jobId]: data.status === 'success' ? 'Saved!' : data.status === 'already_saved' ? 'Already saved.' : 'Error saving.' }));
    setActionLoading(a => ({ ...a, [jobId]: '' }));
  };

  const handleSort = (newSortBy: string) => {
    if (newSortBy === sortBy) {
      // Toggle sort order if clicking the same sort option
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      // Set new sort by and default to descending order
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
    // Trigger a new search with the updated sorting
    handleSearch();
  };

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        keyword: searchParams.keyword,
        location: searchParams.location,
        platform: searchParams.platform,
        page: page.toString(),
        sort_by: sortBy,
        sort_order: sortOrder
      });
      
      const response = await fetch(`${API_BASE_URL}/api/search?${params}`);
      if (!response.ok) throw new Error('Failed to fetch jobs');
      
      const data = await response.json();
      setJobs(data.jobs);
      setTotalPages(data.pages);
      setLocations(data.locations);
      setPlatforms(data.platforms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
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
                      <option value="">All Locations</option>
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
          
          {/* Sorting Controls */}
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                <span className="text-muted" style={{ whiteSpace: 'nowrap', fontWeight: 500 }}>Sort by:</span>
                <select
                  className="form-select"
                  style={{ minWidth: 240, maxWidth: 320 }}
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [newSortBy, newSortOrder] = e.target.value.split('-');
                    setSortBy(newSortBy);
                    setSortOrder(newSortOrder);
                    handleSearch();
                  }}
                >
                  <option value="date_posted-desc">Date Posted (Newest First)</option>
                  <option value="date_posted-asc">Date Posted (Oldest First)</option>
                  <option value="title-asc">Job Title (A-Z)</option>
                  <option value="title-desc">Job Title (Z-A)</option>
                  <option value="company-asc">Company (A-Z)</option>
                  <option value="company-desc">Company (Z-A)</option>
                  <option value="location-asc">Location (A-Z)</option>
                  <option value="location-desc">Location (Z-A)</option>
                  <option value="match_score-desc">Match Score (Highest First)</option>
                  <option value="match_score-asc">Match Score (Lowest First)</option>
                </select>
              </div>
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
                      {/* Status Dropdown */}
                      <select
                        className="form-select form-select-sm"
                        style={{ width: 110 }}
                        value={jobStatuses[job.id] || job.application_status || 'Open'}
                        onChange={async (e) => {
                          const newStatus = e.target.value;
                          setJobStatuses(s => ({ ...s, [job.id]: newStatus }));
                          setActionLoading(a => ({ ...a, [job.id]: 'apply' }));
                          if (newStatus === 'Applied') {
                            await fetch(`${API_BASE_URL}/api/apply_job/${job.id}`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ status: 'Applied' })
                            });
                            setActionMsg(m => ({ ...m, [job.id]: 'Applied!' }));
                            setJobs(jobs => jobs.map(j => j.id === job.id ? { ...j, application_status: 'Applied' } : j));
                            window.open(job.url, '_blank');
                          } else {
                            await fetch(`${API_BASE_URL}/api/update_application_status/${job.id}`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ status: 'Open' })
                            });
                            setActionMsg(m => ({ ...m, [job.id]: 'Set to Open.' }));
                            setJobs(jobs => jobs.map(j => j.id === job.id ? { ...j, application_status: 'Open' } : j));
                          }
                          setActionLoading(a => ({ ...a, [job.id]: '' }));
                        }}
                      >
                        <option value="Open">Open</option>
                        <option value="Applied">Applied</option>
                      </select>
                    </div>
                  </div>
                  <h6 className="card-subtitle mb-2 text-muted">{job.company}</h6>
                  <div className="d-flex align-items-center text-muted mb-2">
                    <small className="me-3"><i className="bi bi-geo-alt"></i> {job.location}</small>
                    <small className="me-3"><i className="bi bi-globe"></i> {job.platform}</small>
                    <small><i className="bi bi-calendar"></i> {new Date(job.date_posted).toLocaleDateString()}</small>
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
