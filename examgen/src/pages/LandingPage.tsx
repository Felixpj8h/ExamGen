import { useState } from 'react';
import FileDropzone from '../components/FileDropzone';
import LoadingOverlay from '../components/LoadingOverlay';
import { processExamUpload } from '../lib/api';
import {
  getBundleFromProcessResponse,
  isValidExamBundle,
} from '../lib/examStorage';
import type { ProcessExamResponse } from '../types';

interface LandingPageProps {
  onExamReady: (response: ProcessExamResponse) => void;
}

interface UploadErrors {
  examFile?: string;
  solutionsFile?: string;
}

function LandingPage({ onExamReady }: LandingPageProps) {
  const [examFile, setExamFile] = useState<File | null>(null);
  const [solutionsFile, setSolutionsFile] = useState<File | null>(null);
  const [autoGenerateSolutions, setAutoGenerateSolutions] = useState(false);
  const [errors, setErrors] = useState<UploadErrors>({});
  const [submitError, setSubmitError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  function validate(): boolean {
    const nextErrors: UploadErrors = {};
    if (!examFile) {
      nextErrors.examFile = 'Upload an exam PDF to continue.';
    }
    if (!autoGenerateSolutions && !solutionsFile) {
      nextErrors.solutionsFile = 'Upload a solutions PDF or enable auto-generated solutions.';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleStart(): Promise<void> {
    setSubmitError('');
    if (!validate()) {
      return;
    }

    if (!examFile) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await processExamUpload({
        examFile,
        solutionsFile,
        autoGenerateSolutions,
      });
      const bundle = getBundleFromProcessResponse(response);
      if (!isValidExamBundle(bundle)) {
        throw new Error('The backend did not return an exam bundle.');
      }
      onExamReady(response);
    } catch (error) {
      console.error('Failed to process exam upload:', error);
      setSubmitError(error instanceof Error ? error.message : 'Failed to process exam upload.');
    } finally {
      setIsLoading(false);
    }
  }

  const canStart = Boolean(examFile) && (autoGenerateSolutions || Boolean(solutionsFile));

  return (
    <main className="landing-page">
      <div className={`landing-shell ${isLoading ? 'is-blurred' : ''}`}>
        <div className="landing-glow" />
        <header className="landing-header">
          <div className="eg-logo">EG</div>
        </header>

        <div className="landing-center">
          <div className="landing-content">
            <div className="landing-copy">
              <p className="landing-kicker">AI-assisted practice</p>
              <h1 className="landing-title">Exam Generator</h1>
              <p className="landing-subtitle">
                Upload an exam and solutions to generate a mock exam experience.
              </p>
            </div>

            <div className="upload-card">
              <div className="upload-grid">
                <FileDropzone
                  label="Exam PDF"
                  helperText="Drag and drop your exam PDF here, or click to browse"
                  file={examFile}
                  onFileChange={(file) => {
                    setExamFile(file);
                    setErrors((current) => ({ ...current, examFile: '' }));
                  }}
                  required
                  error={errors.examFile}
                />
                <FileDropzone
                  label="Solutions PDF"
                  helperText="Drag and drop your solution PDF here, or click to browse"
                  file={solutionsFile}
                  onFileChange={(file) => {
                    setSolutionsFile(file);
                    setErrors((current) => ({ ...current, solutionsFile: '' }));
                  }}
                  required={!autoGenerateSolutions}
                  optionalTone={autoGenerateSolutions}
                  error={errors.solutionsFile}
                />
              </div>

              <div className="toggle-panel">
                <div className="toggle-row">
                  <div>
                    <label htmlFor="auto-generate-solutions" className="toggle-title">
                      Auto-generate solutions
                    </label>
                    <p className="toggle-help">
                      Use this if you do not have a solution PDF. You can review generated solutions before grading.
                    </p>
                  </div>
                  <button
                    id="auto-generate-solutions"
                    type="button"
                    role="switch"
                    aria-label="Auto-generate solutions"
                    aria-checked={autoGenerateSolutions}
                    onClick={() => {
                      setAutoGenerateSolutions((enabled) => !enabled);
                      setErrors((current) => ({ ...current, solutionsFile: '' }));
                    }}
                    className={`toggle-switch ${autoGenerateSolutions ? 'is-on' : ''}`}
                  >
                    <span className="toggle-knob" />
                  </button>
                </div>
              </div>

              {submitError && (
                <div className="upload-error" role="alert" aria-live="polite">
                  {submitError}
                </div>
              )}

              <div className="start-row">
                <button
                  type="button"
                  onClick={handleStart}
                  disabled={!canStart || isLoading}
                  className="start-button"
                >
                  Start
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isLoading && <LoadingOverlay />}
    </main>
  );
}

export default LandingPage;

