const API_BASE_URL =
  (typeof process !== 'undefined' &&
    process.env &&
    (process.env.REACT_APP_API_BASE_URL || process.env.VITE_API_BASE_URL)) ||
  '';

export async function processExamUpload({
  examFile,
  solutionsFile = null,
  autoGenerateSolutions,
}) {
  const formData = new FormData();
  formData.append('exam_pdf', examFile);
  if (solutionsFile) {
    formData.append('solutions_pdf', solutionsFile);
  }
  formData.append('auto_generate_solutions', String(autoGenerateSolutions));

  const response = await fetch(`${API_BASE_URL}/api/exams/process`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.json();
}

async function getErrorMessage(response) {
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
