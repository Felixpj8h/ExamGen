import type { ProcessExamResponse } from '../types';

const CONFIGURED_API_BASE_URL =
  (typeof process !== 'undefined' &&
    process.env &&
    (process.env.REACT_APP_API_BASE_URL || process.env.VITE_API_BASE_URL)) ||
  '';

function getApiBaseUrl(): string {
  if (CONFIGURED_API_BASE_URL) {
    return CONFIGURED_API_BASE_URL;
  }
  if (
    typeof window !== 'undefined' &&
    window.location &&
    window.location.hostname === 'localhost' &&
    window.location.port === '3000'
  ) {
    return 'http://localhost:8000';
  }
  return '';
}

export function getApiUrl(path: string): string {
  const normalizedPath = String(path || '');
  if (/^https?:\/\//i.test(normalizedPath)) {
    return normalizedPath;
  }
  return `${getApiBaseUrl()}${normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`}`;
}

export async function processExamUpload({
  examFile,
  solutionsFile = null,
  autoGenerateSolutions,
  generateNewExam = false,
}: {
  examFile: File;
  solutionsFile?: File | null;
  autoGenerateSolutions: boolean;
  generateNewExam?: boolean;
}): Promise<ProcessExamResponse> {
  const formData = new FormData();
  formData.append('exam_pdf', examFile);
  if (solutionsFile) {
    formData.append('solutions_pdf', solutionsFile);
  }
  formData.append('auto_generate_solutions', String(autoGenerateSolutions));
  formData.append('generate_new_exam', String(generateNewExam));

  const response = await fetch(getApiUrl('/api/exams/process'), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const payload = await response.json();
      return payload.detail || payload.message || `Upload failed with status ${response.status}.`;
    }
    const text = await response.text();
    return text || `Upload failed with status ${response.status}.`;
  } catch (error) {
    console.error('Failed to parse upload error response:', error);
    return `Upload failed with status ${response.status}.`;
  }
}
