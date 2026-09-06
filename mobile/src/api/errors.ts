import axios from 'axios';

export type ApiErrorCode =
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'AUTH_ERROR'
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'RATE_LIMITED'
  | 'SERVER_ERROR'
  | 'UNKNOWN_ERROR';

export class ApiError extends Error {
  readonly code: ApiErrorCode | string;
  readonly status?: number;
  readonly fieldErrors?: Record<string, string>;

  constructor(message: string, code: ApiErrorCode | string, status?: number, fieldErrors?: Record<string, string>) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function detailMessage(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
    return detail.message;
  }
  return undefined;
}

export function parseApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (!axios.isAxiosError(error)) {
    return error instanceof Error
      ? new ApiError(error.message, 'UNKNOWN_ERROR')
      : new ApiError('Something went wrong. Please try again.', 'UNKNOWN_ERROR');
  }
  if (!error.response) {
    return new ApiError(
      error.code === 'ECONNABORTED' ? 'The request took too long. Please try again.' : 'Unable to connect to the server. Please check your internet connection.',
      error.code === 'ECONNABORTED' ? 'TIMEOUT' : 'NETWORK_ERROR',
    );
  }
  const status = error.response.status;
  const body = error.response.data as { detail?: unknown; message?: unknown; error?: { message?: unknown; code?: string }; } | undefined;
  const detail = body?.detail as { message?: unknown; code?: string; } | undefined;
  const backendCode = typeof detail?.code === 'string' ? detail.code : body?.error?.code;
  const message = detailMessage(body?.error?.message) ?? detailMessage(body?.detail) ?? detailMessage(body?.message);
  const defaults: Record<number, [ApiErrorCode, string]> = {
    401: ['AUTH_ERROR', 'Your session has expired. Please log in again.'],
    403: ['AUTH_ERROR', 'You do not have permission to perform this action.'],
    404: ['NOT_FOUND', 'The requested item was not found.'],
    409: ['CONFLICT', 'This request conflicts with existing data.'],
    422: ['VALIDATION_ERROR', 'Please check the information entered.'],
    429: ['RATE_LIMITED', 'Too many requests. Please try again later.'],
  };
  const [code, fallback] = defaults[status] ?? (status >= 500 ? ['SERVER_ERROR', 'Something went wrong on the server. Please try again.'] : ['UNKNOWN_ERROR', 'The request could not be completed.']);
  return new ApiError(message ?? fallback, backendCode ?? code, status);
}
