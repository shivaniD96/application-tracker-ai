'use client';

import React, { useEffect, useState } from 'react';

interface Application {
  id: number;
  job_id: number;
  title: string;
  status: string;
  applied_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchApps() {
      setLoading(true);
      console.log(`${API_BASE_URL}/api/tracker`);
      const res = await fetch(`${API_BASE_URL}/api/tracker`);
      const data = await res.json();
      setApps(data.applications || []);
      setLoading(false);
    }
    fetchApps();
  }, []);

  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <h2 className="display-5 mb-4 text-primary">Application Tracker</h2>
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              {loading ? (
                <div>Loading...</div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Date Applied</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {apps.map(app => (
                        <tr key={app.id}>
                          <td>{app.job_id}</td>
                          <td>{app.title}</td>
                          <td>
                            <span className={`badge ${app.status === 'Applied' ? 'bg-primary' : app.status === 'Rejected' ? 'bg-danger' : 'bg-warning'}`}>{app.status}</span>
                          </td>
                          <td>{app.applied_at}</td>
                          <td>
                            {/* Actions placeholder */}
                            <button className="btn btn-sm btn-primary" disabled>
                              <i className="bi bi-save"></i>
                            </button>
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
