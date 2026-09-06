export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface User {
  id: string;
  full_name: string;
  email: string;
  mobile: string;
  status: 'ACTIVE' | 'DEACTIVATED';
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UploadResponse {
  image_id: string;
  url: string;
}

export interface TryOnJob {
  id: string;
  user_id: string;
  person_image_id: string;
  fabric_image_id: string;
  garment_type: string;
  garment_style: string;
  gender: string | null;
  status: JobStatus;
  error_message: string | null;
  provider: string | null;
  model_version: string | null;
  result_url: string | null;
  result_image_id: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface HistoryItem {
  id: string;
  job_id: string;
  person_image_url: string | null;
  fabric_image_url: string | null;
  result_url: string;
  garment_type: string;
  garment_style: string;
  gender: string | null;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

export interface CreditTransaction {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  reference_id: string | null;
  description: string;
  created_at: string;
}

export interface Credits {
  balance: number;
  total_used: number;
  total_added: number;
  transactions: CreditTransaction[];
}
