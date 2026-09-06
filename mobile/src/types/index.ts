export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type TryOnStatus =
  | 'IDLE'
  | 'UPLOADING_PERSON'
  | 'PERSON_UPLOADED'
  | 'UPLOADING_FABRIC'
  | 'FABRIC_UPLOADED'
  | 'READY_TO_GENERATE'
  | 'QUEUED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED';

export interface User {
  id: string;
  full_name: string;
  email: string;
  mobile: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiJob {
  id: string;
  user_id: string;
  person_image_id: string | null;
  fabric_image_id: string | null;
  garment_type: string | null;
  garment_style: string | null;
  gender: string | null;
  status: JobStatus;
  error_message: string | null;
  provider: string | null;
  model_version: string | null;
  result_url: string | null;
  result_image_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TryOnDraft {
  gender: 'MEN' | 'WOMEN' | 'KIDS';
  garmentId: string | null;
  styleId: string | null;
  personImageUri: string | null;
  fabricImageUri: string | null;
  personImageUrl: string | null;
  fabricImageUrl: string | null;
  personImageId: string | null;
  fabricImageId: string | null;
  jobId: string | null;
  resultUrl: string | null;
  status: TryOnStatus;
  error: string | null;
}
