// components/BottomBar.tsx

import React from 'react';
import { View, TouchableOpacity } from 'react-native';
import { useRouter, useSegments } from 'expo-router'; // <-- Expo Router hooks
import { Ionicons } from '@expo/vector-icons';

import { styles } from './styles/BottomBarStyle';
import { useAuth } from '@/app/_layout'; // <-- The correct auth hook
import { UserRole } from '@/models/User.types';
import { customerTabs, hairdresserTabs } from '@/constants/tabsConfig'; // <-- Our new config

const BottomTabBar: React.FC = () => {
  const router = useRouter();
  const segments = useSegments(); // Gets the current URL path segments, e.g., ['(app)', '(customer)', 'home']
  const { userInfo } = useAuth();

  // Determine which set of tabs to display
  const isCustomer = userInfo?.customer?.user?.role === UserRole.CUSTOMER;
  const tabs = isCustomer ? customerTabs : hairdresserTabs;

  // The last segment of the path is the current screen name
  const currentTabName = segments[segments.length - 1];

  const handleTabPress = (path: string) => {
    // Use the router to navigate to the tab's path
    router.push(path as `http${string}`);
  };

  const renderIcon = (iconName: string, isActive: boolean) => (
    <Ionicons
      name={iconName as any}
      size={24}
      style={isActive ? styles.activeIcon : styles.inactiveIcon}
    />
  );

  return (
    <View style={styles.container}>
      {tabs.map((tab) => {
        const isActive = currentTabName === tab.name;
        return (
          <TouchableOpacity
            key={tab.name}
            style={styles.tabItem}
            onPress={() => handleTabPress(tab.path)}
          >
            {renderIcon(isActive ? tab.activeIcon : tab.icon, isActive)}
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

export default BottomTabBar;