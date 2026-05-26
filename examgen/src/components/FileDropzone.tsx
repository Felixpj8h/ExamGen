import { useId, useRef, useState } from 'react';

interface FileDropzoneProps {
  label: string;
  helperText: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  required: boolean;
  optionalTone?: boolean;
  error?: string;
}

function FileDropzone({
  label,
  helperText,
  file,
  onFileChange,
  required,
  optionalTone = false,
  error,
}: FileDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState('');
  const visibleError = error || localError;

  function selectFile(nextFile?: File | null) {
    setLocalError('');
    if (!nextFile) {
      onFileChange(null);
      return;
    }
    if (nextFile.type !== 'application/pdf' && !nextFile.name.toLowerCase().endsWith('.pdf')) {
      setLocalError('Only PDF files are supported.');
      return;
    }
    onFileChange(nextFile);
  }

  return (
    <div className="file-zone">
      <div className="file-zone-header">
        <label htmlFor={inputId} className="file-zone-label">
          {label}
        </label>
        <span className={`file-zone-badge ${required ? 'is-required' : 'is-optional'}`}>
          {required ? 'Required' : 'Optional'}
        </span>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          selectFile(event.dataTransfer.files?.[0]);
        }}
        aria-describedby={`${inputId}-helper ${inputId}-error`}
        className={`file-drop-target ${
          visibleError
            ? 'has-error'
            : isDragging
              ? 'is-dragging'
              : optionalTone
                ? 'is-optional'
                : ''
        }`}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          className="visually-hidden"
          onChange={(event) => selectFile(event.target.files?.[0])}
        />

        <div className="file-zone-content">
          <div className="file-zone-icon">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 3v5a2 2 0 0 0 2 2h5" />
              <path d="M7 17.5h10" />
              <path d="M7 14h10" />
              <path d="M6 3h8l7 7v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
            </svg>
          </div>

          {file ? (
            <div>
              <p className="file-name">{file.name}</p>
              <p className="file-size">{formatFileSize(file.size)}</p>
              <button
                type="button"
                className="remove-file-button"
                onClick={(event) => {
                  event.stopPropagation();
                  onFileChange(null);
                  if (inputRef.current) {
                    inputRef.current.value = '';
                  }
                }}
              >
                Remove file
              </button>
            </div>
          ) : (
            <div>
              <p id={`${inputId}-helper`} className="file-zone-helper">
                {helperText}
              </p>
              <p className="file-zone-format">PDF only</p>
            </div>
          )}
        </div>
      </div>

      <p id={`${inputId}-error`} className={`file-zone-error ${visibleError ? 'is-visible' : ''}`} aria-live="polite">
        {visibleError || 'No error'}
      </p>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '';
  }
  const megabytes = bytes / (1024 * 1024);
  return `${megabytes.toFixed(megabytes >= 10 ? 0 : 1)} MB`;
}

export default FileDropzone;
