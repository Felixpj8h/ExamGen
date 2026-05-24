function LoadingOverlay() {
  const steps = [
    'Extracting PDF text',
    'Identifying exam questions',
    'Matching official solutions',
    'Preparing your mock exam workspace',
  ];

  return (
    <div
      className="loading-overlay"
      role="status"
      aria-live="polite"
      aria-label="Generating your mock exam"
    >
      <div className="loading-card">
        <div className="loading-card-glow" />
        <div className="loading-icon-wrap">
          <div className="loading-ring loading-ring-large" />
          <div className="loading-ring loading-ring-small" />
          <div className="loader-orbit">
            <span className="loader-page loader-page-one" />
            <span className="loader-page loader-page-two" />
            <span className="loader-page loader-page-three" />
          </div>
          <div className="loading-document">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 3v5a2 2 0 0 0 2 2h5" />
              <path d="M8 14h8" />
              <path d="M8 17h5" />
              <path d="M6 3h8l7 7v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
            </svg>
          </div>
        </div>
        <h2 className="loading-title">
          Generating your mock exam...
        </h2>
        <p className="loading-text">
          Extracting questions, matching solutions, and preparing your workspace.
        </p>
        <div className="loading-progress" aria-hidden="true">
          <div className="loading-progress-track">
            <div className="loading-progress-bar" />
          </div>
          <div className="loading-step-list">
            {steps.map((step, index) => (
              <span key={step} className={`loading-step loading-step-${index + 1}`}>
                {step}
              </span>
            ))}
          </div>
        </div>
        <div className="loading-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}

export default LoadingOverlay;
