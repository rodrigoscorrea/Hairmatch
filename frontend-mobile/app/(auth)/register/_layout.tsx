// app/(auth)/register/_layout.tsx
import { Stack } from 'expo-router';
import { RegistrationProvider } from '../../../contexts/RegistrationContext';

export default function RegisterLayout() {
  return (
    <RegistrationProvider>
      <Stack screenOptions={{ headerShown: false }} />
    </RegistrationProvider>
  );
}