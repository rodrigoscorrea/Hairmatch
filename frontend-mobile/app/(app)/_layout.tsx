// app/(app)/_layout.tsx
import { Stack } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { Redirect } from 'expo-router';

export default function AppLayout() {
  const { userToken, isLoading } = useAuth();

  if (!isLoading && !userToken) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }} />
  );
}