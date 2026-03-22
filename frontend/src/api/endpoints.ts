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
