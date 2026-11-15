import { Redirect } from 'expo-router';
import Gallery from '@/features/gallery/Screen';

export default function GalleryRoute() {
  return __DEV__ ? <Gallery /> : <Redirect href="/" />;
}
