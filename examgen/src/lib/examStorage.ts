import { getApiUrl } from './api';
import type { ExamBundle, ExamImage, ProcessExamResponse } from '../types';

const BUNDLE_STORAGE_KEY = 'exam-generator:last-bundle';
const EXAM_ID_STORAGE_KEY = 'exam-generator:last-exam-id';

export function getBundleFromProcessResponse(response: ProcessExamResponse): ExamBundle | null {
  return response?.bundle || response?.exam_bundle || response?.examBundle || null;
}

export function isValidExamBundle(bundle: unknown): bundle is ExamBundle {
  return Boolean(
    bundle &&
      typeof bundle === 'object' &&
      Array.isArray((bundle as { questions?: unknown }).questions),
  );
}

export function storeExamBundle(bundle: ExamBundle | null, examId?: string | null): void {
  try {
    window.localStorage.setItem(
      BUNDLE_STORAGE_KEY,
      JSON.stringify(withExamAssetUrls(bundle, examId)),
    );
    if (examId) {
      window.localStorage.setItem(EXAM_ID_STORAGE_KEY, examId);
    }
  } catch (error) {
    console.warn('Could not store generated exam bundle:', error);
  }
}

export function loadStoredExamBundle(): ExamBundle | null {
  try {
    const stored = window.localStorage.getItem(BUNDLE_STORAGE_KEY);
    if (!stored) {
      return null;
    }
    const parsed = JSON.parse(stored);
    return isValidExamBundle(parsed) ? withExamAssetUrls(parsed, loadStoredExamId()) : null;
  } catch (error) {
    console.warn('Could not load stored exam bundle:', error);
    return null;
  }
}

export function loadStoredExamId(): string | null {
  try {
    return window.localStorage.getItem(EXAM_ID_STORAGE_KEY);
  } catch (error) {
    console.warn('Could not load stored exam id:', error);
    return null;
  }
}

export function setMockExamLocation(): void {
  if (window.location.hash !== '#mock-exam') {
    window.history.pushState(null, '', '#mock-exam');
  }
}

export function withExamAssetUrls<T extends ExamBundle | null>(bundle: T, examId?: string | null): T {
  if (!isValidExamBundle(bundle) || !examId) {
    return bundle;
  }

  return {
    ...bundle,
    questions: bundle.questions.map((question) => ({
      ...question,
      images: Array.isArray(question.images)
        ? question.images.map((image) => withExamAssetUrl(image, examId))
        : question.images,
    })),
  } as T;
}

function withExamAssetUrl(image: ExamImage, examId: string): ExamImage {
  if (!image || typeof image !== 'object') {
    return image;
  }

  const src = String(image.src || '');
  if (src.startsWith(`/api/exams/${examId}/assets/`)) {
    return {
      ...image,
      src: getApiUrl(src),
    };
  }
  if (src.startsWith('/sample-assets/')) {
    return {
      ...image,
      src: getApiUrl(`/api/exams/${examId}/assets/${src.slice('/sample-assets/'.length)}`),
    };
  }

  const path = String(image.path || '');
  if (path.startsWith('assets/')) {
    return {
      ...image,
      src: getApiUrl(`/api/exams/${examId}/assets/${path.slice('assets/'.length)}`),
    };
  }

  return image;
}

