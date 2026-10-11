// app/(app)/_layout.tsx
import { Stack } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { Redirect } from 'expo-router';
import { usePushNotifications } from '@/hooks/usePushNotifications';

export default function AppLayout() {
  const { userToken, isLoading } = useAuth();
  usePushNotifications();

  if (!isLoading && !userToken) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }} />
  );
}