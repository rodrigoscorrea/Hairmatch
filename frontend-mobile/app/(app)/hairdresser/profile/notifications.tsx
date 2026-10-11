// app/(app)/hairdresser/profile/notifications.tsx
import { useRouter } from 'expo-router';
import AlertList from '@/components/alerts/AlertList';

export default function HairdresserNotificationsScreen() {
  const router = useRouter();

  // After a tap on a push the inbox can be the only screen of the stack: then the way back is the settings.
  return (
    <AlertList onBack={() => (router.canGoBack() ? router.back() : router.replace('/(app)/hairdresser/profile/settings'))} />
  );
}
