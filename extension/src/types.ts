export type Language = 'python' | 'rust';
export interface Problem {
  id: string; number: number; title: string; topic: string; difficulty: string;
  description: string; templates: Record<Language, string>;
  examples: {input: unknown; expected: unknown}[]; hints: string[];
  approach: string; complexity: string; pitfalls: string; version: number; test_count: number;
}
export interface Lesson {id: string; title: string; topic: string; body: string}
export interface Knowledge {id: string; title: string; question: string; points: string[]}
export interface Progress {bookmark?: number; mastery?: string; notes?: string; review_at?: string; seen_answer?: number}
export interface State {statuses: Record<string, string>; progress: Record<string, Progress>; knowledge: Record<string, {answer: string; mastery: string}>}
export interface Bootstrap {problems: Problem[]; lessons: Lesson[]; knowledge: Knowledge[]; mastery: string[]; state: State; environment: {python: string; rust: boolean; data_dir: string}}
export interface Draft {problem_id: string; language: Language; code: string; updated_at: string}
export interface Submission {id: string; code: string; language: Language; mode: string; created_at: string; result: JudgeResult}
export interface JudgeResult {status: string; passed: number; total: number; message: string; compile_ms: number; execution_ms: number; stderr: string; stdout?: string; cases: {index: number; input: unknown; expected: unknown; actual: unknown; passed: boolean}[]}
