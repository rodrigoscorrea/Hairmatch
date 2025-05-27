import React from 'react';
import { View, TouchableOpacity } from 'react-native';
import { styles } from './styles/BottomBarStyle';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { useBottomTab } from '../contexts/BottomTabContext';

// Define tab configuration
const tabs = [
  {
    name: 'Home',
    icon: 'home-outline',
    activeIcon: 'home',
    route: 'CustomerHome'
  },
  {
    name: 'Search',
    icon: 'search-outline',
    activeIcon: 'search',
    route: 'Search'
  },
  {
    name: 'Reserves',
    icon: 'calendar-outline',
    activeIcon: 'calendar',
    route: 'Reserves'
  },
  {
    name: 'Profile',
    icon: 'person-outline',
    activeIcon: 'person',
    route: 'Profile'
  }
];

const hairdresserTabs = [
  {
    name: 'HairdresserProfile',
    icon: 'person-outline',
    activeIcon: 'person',
    route: 'HairdresserProfile'
  }
]

const BottomTabBar: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { activeTab, setActiveTab, customer, hairdresser } = useBottomTab();

  const isActive = (tabRoute: string): boolean => {
    // If activeTab from context is provided, use it, otherwise use the current route name
    if (activeTab) {
      return activeTab === tabRoute;
    }
    return route.name === tabRoute;
  };

  const handleTabPress = (tabRoute: string): void => {
    if (!isActive(tabRoute)) {
      setActiveTab(tabRoute);
      if (customer) {
        // @ts-ignore - We're ignoring the type error because navigation props vary
        navigation.navigate(tabRoute, { customer });
      } else if (hairdresser) {
        // @ts-ignore - We're ignoring the type error because navigation props vary
        navigation.navigate(hairdresserTabs, { hairdresser });
      }else {
        // @ts-ignore
        navigation.navigate(tabRoute);
      }
    }
  };

  const renderIcon = (iconName: string, isActive: boolean) => {
    return (
      <Ionicons
        name={iconName as any}
        size={24}
        style={isActive ? styles.activeIcon : styles.inactiveIcon}
      />
    );
  };

  return (
    <View style={styles.container}>
      {customer ? (
        <>
          {tabs.map((tab) => (
            <TouchableOpacity
              key={tab.name}
              style={styles.tabItem}
              onPress={() => handleTabPress(tab.route)}
            >
              {renderIcon(
                isActive(tab.route) ? tab.activeIcon : tab.icon,
                isActive(tab.route)
              )}
            </TouchableOpacity>
          ))}
        </>
      ):(
        <>
          {hairdresserTabs.map((tab) => (
            <TouchableOpacity
              key={tab.name}
              style={styles.tabItem}
              onPress={() => handleTabPress(tab.route)}
            >
              {renderIcon(
                isActive(tab.route) ? tab.activeIcon : tab.icon,
                isActive(tab.route)
              )}
            </TouchableOpacity>
          ))}
        </>
      )}
      
    </View>
  );
};

export default BottomTabBar;