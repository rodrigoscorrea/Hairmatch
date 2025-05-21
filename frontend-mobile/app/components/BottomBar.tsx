import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
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

const BottomTabBar: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { activeTab, setActiveTab, customer } = useBottomTab();

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
      } else {
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
        color={isActive ? '#FF6600' : '#666'}
      />
    );
  };

  return (
    <View style={styles.container}>
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
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#FDF0E7',
    height: 60,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabText: {
    fontSize: 10,
    marginTop: 3,
    color: '#666',
  },
  activeTabText: {
    color: '#FF6600',
    fontWeight: 'bold',
  },
});

export default BottomTabBar;