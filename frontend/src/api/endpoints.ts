/**
 * Typed wrappers for every Flask API endpoint the React app calls.
 * Add new endpoints here — never call apiClient directly from components.
 */

import { apiClient } from './client'
import type {
  User,
  EnrolledClassesResponse,
  ClassDetailResponse,
  EnrollResponse,
  ChaptersResponse,
  ExercisesResponse,
  Exercise,
  ResourcesResponse,
  LeaderboardResponse,
  GradeResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface SignInPayload {
  email: string
  password: string
}

export interface SignUpPayload {
  name: string
  email: string
  password: string
}

export interface AuthResponse extends User {
  token?: string
  refresh_token?: string
  success?: boolean
  pending_approval?: boolean
  message?: string
  requires_password_reset?: boolean
}

export const authApi = {
  signIn: (payload: SignInPayload) =>
    apiClient.post<AuthResponse>('/users/signin', payload),

  signUp: (payload: SignUpPayload) =>
    apiClient.post<AuthResponse>('/users/signup', payload),

  forgotPassword: (email: string) =>
    apiClient.post<{ success: boolean; message: string }>('/users/forgot-password', { email }),

  resetPassword: (token: string, email: string, newPassword: string) =>
    apiClient.post<{ success: boolean; message: string }>('/users/reset-password', {
      token,
      email,
      newPassword,
    }),

  getSsoProviders: (domain?: string) =>
    apiClient.get<{ providers: Array<{ id: string; name: string; icon?: string }> }>(
      `/sso/providers${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
    ),
}

// ---------------------------------------------------------------------------
// Classes
// ---------------------------------------------------------------------------

export const classesApi = {
  getEnrolled: () =>
    apiClient.get<EnrolledClassesResponse>('/classes/enrolled'),

  getDetail: (classId: string) =>
    apiClient.get<ClassDetailResponse>(`/classes/${classId}`),

  enroll: (classId: string) =>
    apiClient.post<EnrollResponse>('/classes/enroll', { class_id: classId }),

  create: (payload: { name: string; description?: string }) =>
    apiClient.post('/classes', payload),

  delete: (classId: string) =>
    apiClient.del(`/classes/${classId}/delete`),

  getProfessorClasses: () =>
    apiClient.get('/user/classes'),
}

// ---------------------------------------------------------------------------
// Chapters
// ---------------------------------------------------------------------------

export const chaptersApi = {
  getByClass: (classId: string) =>
    apiClient.get<ChaptersResponse>(`/classes/${classId}/chapters`),

  getById: (chapterId: string) =>
    apiClient.get<{ chapter_id: string; title: string; description?: string; class_id: string; pdf_url?: string; source_type?: string; created_at?: string }>(`/chapters/${chapterId}`),

  getExercises: (chapterId: string) =>
    apiClient.get<ExercisesResponse>(`/chapters/${chapterId}/exercises`),
}

// ---------------------------------------------------------------------------
// Exercises
// ---------------------------------------------------------------------------

export const exercisesApi = {
  getById: (exerciseId: string) =>
    apiClient.get<Exercise>(`/exercises/${exerciseId}`),

  grade: (exerciseId: string, payload: { code: string; class_id?: string }) =>
    apiClient.post<GradeResponse>(`/exercises/${exerciseId}/grade`, payload),
}

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------

export const resourcesApi = {
  getByClass: (classId: string) =>
    apiClient.get<ResourcesResponse>(`/classes/${classId}/resources`),
}

// ---------------------------------------------------------------------------
// Leaderboard
// ---------------------------------------------------------------------------

export const leaderboardApi = {
  getAverage: (classId: string) =>
    apiClient.get<LeaderboardResponse>(`/classes/${classId}/leaderboard/average`),

  getByExercise: (classId: string, exerciseId: string) =>
    apiClient.get<LeaderboardResponse>(`/classes/${classId}/leaderboard/exercise/${exerciseId}`),
}
