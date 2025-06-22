import { Tabs } from 'expo-router';
import BottomTabBar from '@/components/BottomBar';
import { hairdresserTabs } from '@/constants/tabsConfig';

export default function HairdresserTabLayout() {
  return (
    <Tabs 
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <BottomTabBar {...props} />}
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