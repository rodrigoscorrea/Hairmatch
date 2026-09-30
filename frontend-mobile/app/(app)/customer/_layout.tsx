import { Redirect, Tabs } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { HAIRDRESSER_HOME } from '@/utils/routes';
import BottomTabBar from '@/components/BottomBar';
import { customerTabs } from '@/constants/tabsConfig'; 

export default function CustomerTabLayout() {
  const { userInfo } = useAuth();

  // A user of the other role only lands here through a typed URL or an old link.
  if (userInfo && !userInfo.customer) {
    return <Redirect href={HAIRDRESSER_HOME} />;
  }

  return (
    // Use the `tabBar` prop to provide your custom component
    <Tabs 
      screenOptions={{ headerShown: false }}
      tabBar={() => <BottomTabBar />}
    >

      {customerTabs.map((tab) => (
         <Tabs.Screen
            key={tab.name}
            name={tab.name}
            options={{
              title: tab.name,
            }}
         />
      ))}
      <Tabs.Screen name="service-booking" options={{ href: null }} />
      <Tabs.Screen name="review/[id]" options={{ href: null }} />
    </Tabs>
  );
}