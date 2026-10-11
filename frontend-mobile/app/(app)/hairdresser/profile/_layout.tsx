import { Stack } from 'expo-router';

// A direct entry (a push tap with the app closed) lands on a screen of this stack with no history; the profile goes below it.
export const unstable_settings = { initialRouteName: 'index' };

export default function ProfileStackLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="settings" />
      <Stack.Screen name="gallery" />
      <Stack.Screen name="notifications" />
      <Stack.Screen name="reviews" />
    </Stack>
  );
}
