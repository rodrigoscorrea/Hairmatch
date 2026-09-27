import { Stack } from 'expo-router';
import { RegistrationProvider } from '../../contexts/RegistrationContext';

export default function AuthLayout() {
  return (
    <RegistrationProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" />
        <Stack.Screen name="register" />
      </Stack>
    </RegistrationProvider>
  );
}
