import type { ReactNode } from 'react';

export type InteractionType = 'free_text' | 'true_false' | 'multiple_choice' | 'matrix_choice' | 'numeric' | string;

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

export interface GraphDiagramNode {
  id: string;
  label?: string | null;
}

export interface GraphDiagramEdge {
  id?: string | null;
  source: string;
  target: string;
  label?: string | null;
  weight?: string | number | null;
  directed?: boolean | null;
}

export interface GraphDiagram {
  id: string;
  type: 'graph';
  title?: string | null;
  nodes: GraphDiagramNode[];
  edges: GraphDiagramEdge[];
  start_node?: string | null;
  highlighted_nodes?: string[];
  highlighted_edges?: string[];
}

export interface TreeDiagramNode {
  id: string;
  label?: string | null;
  children?: TreeDiagramNode[];
}

export interface TreeDiagram {
  id: string;
  type: 'tree';
  title?: string | null;
  root: TreeDiagramNode;
  highlighted_nodes?: string[];
}

export type ExamDiagram = GraphDiagram | TreeDiagram;

export interface AnswerItem {
  id: string;
  label?: string | null;
  text?: string | null;
  points?: number | null;
  interaction_type?: InteractionType | null;
  choices?: string[];
  matrix?: {
    rows?: string[];
    columns?: string[];
  };
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
  matrix?: {
    rows?: string[];
    columns?: string[];
  };
  diagrams?: ExamDiagram[];
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
