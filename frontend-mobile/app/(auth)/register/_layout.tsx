// app/(auth)/register/_layout.tsx
import { Stack } from 'expo-router';

// O RegistrationProvider fica em app/(auth)/_layout.tsx, para a tela de login também usar o contexto.
export default function RegisterLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }} />
  );
}
