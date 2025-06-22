import { Tabs } from 'expo-router';
import BottomTabBar from '@/components/BottomBar';
import { customerTabs } from '@/constants/tabsConfig'; 

export default function CustomerTabLayout() {
  return (
    // Use the `tabBar` prop to provide your custom component
    <Tabs 
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <BottomTabBar {...props} />}
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
      
      <Tabs.Screen name="hairdresser-profile/[id]" options={{ href: null }} />
      <Tabs.Screen name="service-booking" options={{ href: null }} />
    </Tabs>
  );
}