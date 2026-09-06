import { useMutation, useQueryClient } from '@tanstack/react-query';
import { login, register, forgotPassword, resetPassword } from '../api/auth.api';
import { createTryOn, CreateTryOnInput } from '../api/tryon.api';
import { markAllNotificationsRead, markNotificationRead } from '../api/notifications.api';
import { deactivateAccount, deleteAccount } from '../api/account.api';
import { uploadFabric, uploadPerson, UploadProgressHandler } from '../api/upload.api';

export const useLoginMutation = () => useMutation({ mutationFn: ({ identifier, password }: { identifier: string; password: string }) => login(identifier, password) });
export const useRegisterMutation = () => useMutation({ mutationFn: register });
export const useForgotPasswordMutation = () => useMutation({ mutationFn: forgotPassword });
export const useResetPasswordMutation = () => useMutation({ mutationFn: ({ otp, newPassword }: { otp: string; newPassword: string }) => resetPassword(otp, newPassword) });
export const useCreateTryOnMutation = () => useMutation({ mutationFn: (input: CreateTryOnInput) => createTryOn(input) });
export const useUploadPersonMutation = () => useMutation({ mutationFn: ({ uri, onProgress }: { uri: string; onProgress?: UploadProgressHandler }) => uploadPerson(uri, onProgress) });
export const useUploadFabricMutation = () => useMutation({ mutationFn: ({ uri, onProgress }: { uri: string; onProgress?: UploadProgressHandler }) => uploadFabric(uri, onProgress) });
export const useMarkNotificationReadMutation = () => { const client = useQueryClient(); return useMutation({ mutationFn: markNotificationRead, onSuccess: () => client.invalidateQueries({ queryKey: ['notifications'] }) }); };
export const useMarkAllNotificationsReadMutation = () => { const client = useQueryClient(); return useMutation({ mutationFn: markAllNotificationsRead, onSuccess: () => client.invalidateQueries({ queryKey: ['notifications'] }) }); };
export const useDeactivateAccountMutation = () => useMutation({ mutationFn: deactivateAccount });
export const useDeleteAccountMutation = () => useMutation({ mutationFn: deleteAccount });
