// app/index.tsx
import { Redirect } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { homeRouteFor } from '@/utils/routes';

// "/" has no screen of its own: send the user to the landing screen of their role.
export default function Index() {
  const { userToken, userInfo } = useAuth();
  return <Redirect href={(userToken && homeRouteFor(userInfo)) || '/(auth)/login'} />;
}
