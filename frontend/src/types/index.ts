// ---------------------------------------------------------------------------
// Domain types — mirror the shapes returned by Flask API endpoints
// ---------------------------------------------------------------------------

export interface User {
  id: string
  user_id: string
  name: string
  email: string
  role: 'superadmin' | 'tenant_admin' | 'professor' | 'student'
  tenant_id?: string
  token?: string
}

export interface Class {
  class_id: string
  name: string
  description?: string
  professor_name?: string
  professor_id?: string
  chapter_count?: number
  student_count?: number
  join_code?: string
  created_at?: string
}

export interface Chapter {
  chapter_id: string
  title: string
  class_id: string
  exercise_count?: number
  pdf_url?: string
  source_type?: string
  created_at?: string
}

export interface Exercise {
  exercise_id: string
  chapter_id: string
  title: string
  description?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  exercise_type?: string
  points?: number
}

export interface EnrolledClassesResponse {
  classes: Class[]
}

export interface ClassDetailResponse {
  class: Class
}

export interface EnrollResponse {
  success: boolean
  class_name: string
  class_id: string
}

export interface ApiError {
  error: string
  code?: string
}

export interface Resource {
  resource_id: string
  title: string
  description?: string
  resource_type: 'pdf' | 'tool' | 'dataset' | 'video' | 'article' | 'link' | 'csv' | 'excel' | 'ipynb' | 'json' | 'txt'
  resource_url: string
  is_default?: boolean
  chapter_id?: string
  is_chapter?: boolean
}

export interface LeaderboardEntry {
  user_id: string
  name: string
  score: number
  rank?: number
  average_score?: number
}

export interface ChaptersResponse {
  chapters: Chapter[]
}

export interface ExercisesResponse {
  exercises: Exercise[]
}

export interface ResourcesResponse {
  all_resources: Resource[]
}

export interface LeaderboardResponse {
  leaderboard: LeaderboardEntry[]
}

export interface GradeResponse {
  success: boolean
  score?: number
  feedback?: string
  passed?: boolean
  error?: string
}
