import { Redirect, Tabs } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { CUSTOMER_HOME } from '@/utils/routes';
import BottomTabBar from '@/components/BottomBar';
import { hairdresserTabs } from '@/constants/tabsConfig';

export default function HairdresserTabLayout() {
  const { userInfo } = useAuth();

  // A user of the other role only lands here through a typed URL or an old link.
  if (userInfo && !userInfo.hairdresser) {
    return <Redirect href={CUSTOMER_HOME} />;
  }

  return (
    <Tabs 
      screenOptions={{ headerShown: false }}
      tabBar={() => <BottomTabBar />}
    >
      {/* Generate screens from our central config file */}
      {hairdresserTabs.map((tab) => (
         <Tabs.Screen
            key={tab.name}
            name={tab.name} // This must match the filename, e.g., agenda.tsx
            options={{
              title: tab.name,
            }}
         />
      ))}
       {/* You can add any stack-only (non-tab) screens for hairdressers here later */}
       {/* e.g., <Tabs.Screen name="edit-service" options={{ href: null }} /> */}
    </Tabs>
  );
}