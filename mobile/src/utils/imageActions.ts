import * as FileSystem from 'expo-file-system/legacy';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';

export class ImageActionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ImageActionError';
  }
}

function assertImageUrl(resultUrl: string | null | undefined): asserts resultUrl is string {
  if (!resultUrl || !/^https?:\/\//i.test(resultUrl)) {
    throw new ImageActionError('Generated image is not available yet.');
  }
}

async function downloadToCache(resultUrl: string | null | undefined): Promise<string> {
  assertImageUrl(resultUrl);
  const extension = resultUrl.toLowerCase().includes('.png') ? 'png' : 'jpg';
  const target = `${FileSystem.cacheDirectory}vastrai-result-${Date.now()}.${extension}`;
  const download = await FileSystem.downloadAsync(resultUrl, target);
  if (download.status < 200 || download.status >= 300) {
    throw new ImageActionError('The generated image could not be downloaded.');
  }
  return download.uri;
}

export async function downloadImage(resultUrl: string | null | undefined): Promise<void> {
  try {
    const permission = await MediaLibrary.requestPermissionsAsync();
    if (!permission.granted) {
      throw new ImageActionError('Photo access is required to save the image to your gallery.');
    }
    const localUri = await downloadToCache(resultUrl);
    await MediaLibrary.saveToLibraryAsync(localUri);
  } catch (error) {
    if (error instanceof ImageActionError) throw error;
    throw new ImageActionError('The image could not be saved to your gallery. Please try again.');
  }
}

export async function shareImage(resultUrl: string | null | undefined): Promise<void> {
  try {
    const localUri = await downloadToCache(resultUrl);
    if (!(await Sharing.isAvailableAsync())) {
      throw new ImageActionError('Sharing is not available on this device.');
    }
    await Sharing.shareAsync(localUri, {
      mimeType: localUri.endsWith('.png') ? 'image/png' : 'image/jpeg',
      dialogTitle: 'Share your VastrAI look',
      UTI: localUri.endsWith('.png') ? 'public.png' : 'public.jpeg',
    });
  } catch (error) {
    if (error instanceof ImageActionError) throw error;
    throw new ImageActionError('The image could not be shared. Please try again.');
  }
}
