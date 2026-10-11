// app/(app)/customer/notifications.tsx
import { useRouter } from 'expo-router';
import AlertList from '@/components/alerts/AlertList';

export default function CustomerNotificationsScreen() {
  const router = useRouter();

  return <AlertList onBack={() => router.push('/(app)/customer/profile')} />;
}
