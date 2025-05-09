'use client';

import React, { useEffect, useState, FormEvent } from 'react';

interface Resume {
  filename: string;
  uploaded_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function DetailsPage() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    async function fetchResume() {
      const res = await fetch(`${API_BASE_URL}/api/details`);
      const data = await res.json();
      setResume(data.resume || null);
    }
    fetchResume();
  }, []);

  const handleUpload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setUploading(true);
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem('file') as HTMLInputElement;
    if (!fileInput.files || fileInput.files.length === 0) {
      setError('No file selected');
      setUploading(false);
      return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const res = await fetch(`${API_BASE_URL}/api/details`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.error) {
      setError(data.error);
    } else {
      setResume(data.resume);
    }
    setUploading(false);
  };

  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <h2 className="display-5 mb-4 text-primary">Resume Details</h2>
          <div className="card shadow-sm mb-4">
            <div className="card-body">
              {resume ? (
                <div className="alert alert-info d-flex justify-content-between align-items-center">
                  <div>
                    <i className="bi bi-file-earmark-text me-2"></i>
                    Current Resume: <a href={`/uploads/${resume.filename}`} className="alert-link" target="_blank" rel="noopener noreferrer">{resume.filename}</a>
                    <small className="text-muted ms-2">(Uploaded: {resume.uploaded_at})</small>
                  </div>
                </div>
              ) : (
                <div className="alert alert-warning">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  No resume uploaded yet. Please upload your resume to track your applications.
                </div>
              )}
              <form method="post" encType="multipart/form-data" className="mt-4" onSubmit={handleUpload}>
                <div className="row g-3">
                  <div className="col-md-8">
                    <div className="input-group">
                      <input type="file" name="file" className="form-control" accept=".pdf,.doc,.docx,.txt" required />
                      <button type="submit" className="btn btn-primary" disabled={uploading}>
                        <i className="bi bi-upload me-2"></i>Upload Resume
                      </button>
                    </div>
                    <small className="text-muted d-block mt-2">
                      Supported formats: PDF, DOC, DOCX, TXT (Max size: 5MB)
                    </small>
                  </div>
                </div>
              </form>
              {error && (
                <div className="alert alert-danger mt-3">
                  <i className="bi bi-exclamation-circle me-2"></i>
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
