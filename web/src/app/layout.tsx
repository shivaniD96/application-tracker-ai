import './globals.css';
import type { ReactNode } from 'react';
import Script from 'next/script';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Job Application Tracker</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet" />
      </head>
      <body>
        <div className="d-flex">
          {/* Sidebar */}
          <div className="sidebar bg-dark text-white">
            <div className="sidebar-header p-3">
              <h4 className="mb-0 text-white">JobApp</h4>
              <p className="text-muted small mb-0">Track your job search</p>
            </div>
            <ul className="nav flex-column">
              <li className="nav-item">
                <a className="nav-link" href="/search">
                  <i className="bi bi-search"></i>
                  <span>Search Jobs</span>
                </a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/tracker">
                  <i className="bi bi-list-check"></i>
                  <span>Application Tracker</span>
                </a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/saved_jobs">
                  <i className="bi bi-bookmark"></i>
                  <span>Saved Jobs</span>
                </a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/details">
                  <i className="bi bi-file-earmark-text"></i>
                  <span>Resume Details</span>
                </a>
              </li>
            </ul>
            <div className="sidebar-footer p-3">
              <div className="d-flex align-items-center">
                <i className="bi bi-gear me-2"></i>
                <span>Settings</span>
              </div>
            </div>
          </div>
          {/* Main Content */}
          <div className="main-content" style={{ width: '100%' }}>
            {children}
          </div>
        </div>
        <style>{`
          .sidebar {
            width: 250px;
            min-height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1000;
            transition: all 0.3s;
          }
          .sidebar-header {
            border-bottom: 1px solid rgba(255,255,255,0.1);
          }
          .sidebar .nav-link {
            color: rgba(255,255,255,0.8);
            padding: 0.8rem 1rem;
            display: flex;
            align-items: center;
            transition: all 0.3s;
          }
          .sidebar .nav-link:hover {
            color: #fff;
            background: rgba(255,255,255,0.1);
          }
          .sidebar .nav-link.active {
            color: #fff;
            background: rgba(255,255,255,0.1);
            border-left: 4px solid #0d6efd;
          }
          .sidebar .nav-link i {
            margin-right: 10px;
            font-size: 1.1rem;
          }
          .sidebar-footer {
            position: absolute;
            bottom: 0;
            width: 100%;
            border-top: 1px solid rgba(255,255,255,0.1);
          }
          .main-content {
            margin-left: 250px;
            padding: 20px;
            min-height: 100vh;
            background-color: #f8f9fa;
          }
          @media (max-width: 768px) {
            .sidebar {
              width: 70px;
            }
            .sidebar .nav-link span {
              display: none;
            }
            .sidebar-header h4, .sidebar-header p {
              display: none;
            }
            .main-content {
              margin-left: 70px;
            }
            .sidebar-footer span {
              display: none;
            }
          }
          body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
          }
          .card {
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          }
          .btn {
            font-weight: 500;
          }
          .form-control, .form-select {
            border-radius: 8px;
          }
          .badge {
            font-weight: 500;
          }
        `}</style>
        <Script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
