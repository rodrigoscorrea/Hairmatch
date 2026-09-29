// app/(auth)/register/_layout.tsx
import { Stack } from 'expo-router';

// The RegistrationProvider lives in app/(auth)/_layout.tsx, so the login screen can also use the context.
export default function RegisterLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }} />
  );
}
