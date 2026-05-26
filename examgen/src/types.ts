import type { ReactNode } from 'react';

export type InteractionType = 'free_text' | 'true_false' | 'multiple_choice' | 'numeric' | string;

export type SolutionSource = 'official_solution_pdf' | 'same_pdf' | 'ai_generated' | 'manual' | string;

export interface ExamSolution {
  answer?: string | null;
  explanation?: string | null;
  grading_points?: string[];
  source?: SolutionSource | null;
}

export interface ExamImage {
  id?: string;
  src?: string;
  path?: string;
  alt?: string;
  page_number?: number | null;
  width?: number | null;
  height?: number | null;
}

export interface AnswerItem {
  id: string;
  label?: string | null;
  text?: string | null;
  points?: number | null;
  interaction_type?: InteractionType | null;
  choices?: string[];
  solution?: ExamSolution | null;
}

export interface ExamQuestion {
  id: string;
  question_number: string;
  question_text: string;
  page_start?: number | null;
  page_end?: number | null;
  points?: number | null;
  topic?: string | null;
  context?: string | null;
  interaction_type?: InteractionType | null;
  choices?: string[];
  images?: ExamImage[];
  subquestions?: AnswerItem[];
  solution?: ExamSolution | null;
}

export interface ExamBundle {
  exam: {
    title?: string | null;
    course_code?: string | null;
    source_file?: string | null;
  };
  questions: ExamQuestion[];
  warnings: string[];
}

export interface ProcessExamResponse {
  exam_id?: string | null;
  examId?: string | null;
  status?: string;
  bundle?: ExamBundle;
  exam_bundle?: ExamBundle;
  examBundle?: ExamBundle;
}

export interface ParsedTextBlock {
  type: 'text' | 'code';
  content: string;
  language?: string;
}

export type HighlightedCode = string | ReactNode[];
