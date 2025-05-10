'use client';

import React, { useEffect, useState } from 'react';

interface Application {
  id: number;
  job_id: number;
  company: string;
  location: string;
  referral: string;
  job_link: string;
  status: string;
  referral_mail: string;
  title?: string;
  applied_at?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusLoading, setStatusLoading] = useState<{[id: number]: boolean}>({});
  const [statusMsg, setStatusMsg] = useState<{[id: number]: string}>({});
  const [fileUploading, setFileUploading] = useState(false);
  const [fileUploadMsg, setFileUploadMsg] = useState<string | null>(null);

  useEffect(() => {
    async function fetchApps() {
      setLoading(true);
      setError(null);
      try {
        console.log('Fetching applications from:', `${API_BASE_URL}/api/tracker`);
        const res = await fetch(`${API_BASE_URL}/api/tracker`);
        console.log('Response status:', res.status);
        if (!res.ok) {
          throw new Error(`API error: ${res.status}`);
        }
        const data = await res.json();
        console.log('Fetched applications data:', data);
        if (data.error) {
          throw new Error(data.error);
        }
        setApps(data.applications || []);
      } catch (err) {
        console.error('Error fetching applications:', err);
        setError('Failed to load applications. Please try again later.');
        setApps([]);
      } finally {
        setLoading(false);
      }
    }
    fetchApps();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setFileUploading(true);
    setFileUploadMsg(null);
    try {
      const formData = new FormData();
      formData.append('file', e.target.files[0]);
      console.log('Uploading file:', e.target.files[0].name);
      const res = await fetch(`${API_BASE_URL}/api/upload_applications_excel`, {
        method: 'POST',
        body: formData,
      });
      console.log('Upload response status:', res.status);
      const data = await res.json();
      console.log('Upload response data:', data);
      if (data.status === 'success') {
        setFileUploadMsg('Applications uploaded and updated!');
        // Refresh tracker
        window.location.reload();
      } else {
        setFileUploadMsg('Error: ' + (data.message || 'Upload failed.'));
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      setFileUploadMsg('Error uploading file. Please try again.');
    } finally {
      setFileUploading(false);
    }
  };

  const handleFieldChange = async (app: Application, field: string, value: string) => {
    try {
      // Update locally
      setApps(apps => apps.map(a => a.id === app.id ? { ...a, [field]: value } : a));
      
      // Update backend
      const res = await fetch(`${API_BASE_URL}/api/update_application_status/${app.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          status: field === 'status' ? value : app.status,
          referral_mail: field === 'referral_mail' ? value : app.referral_mail,
          referral: field === 'referral' ? value : app.referral
        })
      });
      
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Show success message
      setStatusMsg(prev => ({ ...prev, [app.id]: 'Saved!' }));
      setTimeout(() => {
        setStatusMsg(prev => ({ ...prev, [app.id]: '' }));
      }, 2000);
    } catch (err) {
      console.error('Error updating application:', err);
      setStatusMsg(prev => ({ ...prev, [app.id]: 'Error saving' }));
    }
  };

  // Add status counts
  const statusCounts = apps.reduce((acc, app) => {
    const status = (app.status || '').toLowerCase();
    if (status === 'applied') acc.applied += 1;
    else if (status === 'rejected') acc.rejected += 1;
    else if (status === 'interview') acc.interview += 1;
    else if (status === 'congrats') acc.congrats += 1;
    return acc;
  }, { applied: 0, rejected: 0, interview: 0, congrats: 0 });

  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <h2 className="display-5 mb-4 text-primary">Application Tracker</h2>
          {/* Status Counters */}
          <div className="mb-3 d-flex gap-4">
            <span className="badge bg-primary">Applied: {statusCounts.applied}</span>
            <span className="badge bg-danger">Rejected: {statusCounts.rejected}</span>
            <span className="badge bg-warning text-dark">Interview: {statusCounts.interview}</span>
            <span className="badge bg-success">Congrats: {statusCounts.congrats}</span>
          </div>
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              <div className="mb-3 d-flex align-items-center gap-3">
                <label className="form-label mb-0">Upload Excel/CSV:</label>
                <input type="file" accept=".xlsx,.xls,.csv" onChange={handleFileUpload} disabled={fileUploading} />
                {fileUploading && <span className="text-muted ms-2">Uploading...</span>}
                {fileUploadMsg && <span className="ms-2 text-success">{fileUploadMsg}</span>}
              </div>
              {(() => { console.log('Loading:', loading, 'Apps:', apps); return null; })()}
              {loading ? (
                <div>Loading...</div>
              ) : error ? (
                <div className="alert alert-danger">{error}</div>
              ) : apps.length === 0 ? (
                <div className="alert alert-info">No applications found.</div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr style={{ backgroundColor: '#f8f9fa' }}>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Company</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Location</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Referral</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Job Link</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Status</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Referral mail</th>
                        <th style={{ fontWeight: 'bold', padding: '12px 16px' }}>Application Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {apps.map(app => (
                        <tr key={app.id} style={{ verticalAlign: 'middle' }}>
                          <td style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: 200 }}>
                            {app.company && app.job_link ? (
                              <>
                                <a href={app.job_link} target="_blank" rel="noopener noreferrer">{app.company}</a>
                              </>
                            ) : app.company ? app.company : '-'}
                          </td>
                          <td style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: 160 }}>{app.location || '-'}</td>
                          <td>
                            <select
                              className="form-select form-select-sm"
                              style={{ width: 90 }}
                              value={app.referral || 'No'}
                              onChange={e => handleFieldChange(app, 'referral', e.target.value)}
                            >
                              <option value="No">No</option>
                              <option value="Yes">Yes</option>
                            </select>
                          </td>
                          <td style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: 120 }}>
                            {app.job_link ? (
                              <a href={app.job_link} target="_blank" rel="noopener noreferrer">Link</a>
                            ) : '-'}
                          </td>
                          <td>
                            <select
                              className="form-select form-select-sm"
                              style={{ width: 120 }}
                              value={app.status || 'Open'}
                              onChange={e => handleFieldChange(app, 'status', e.target.value)}
                            >
                              <option value="Open">Open</option>
                              <option value="Applied">Applied</option>
                              <option value="Rejected">Rejected</option>
                              <option value="Interview">Interview</option>
                              <option value="Congrats">Congrats</option>
                            </select>
                          </td>
                          <td style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: 180 }}>
                            <input
                              type="text"
                              className="form-control form-control-sm"
                              value={app.referral_mail || ''}
                              onChange={e => handleFieldChange(app, 'referral_mail', e.target.value)}
                              style={{ minWidth: 180 }}
                            />
                          </td>
                          <td style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: 120 }}>
                            {app.applied_at ? app.applied_at.slice(0, 10) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
