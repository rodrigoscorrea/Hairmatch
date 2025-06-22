export const customerTabs = [
  {
    name: 'home', // Corresponds to the filename `home.tsx`
    path: '/(app)/(customer)/home', // Full path for navigation
    icon: 'home-outline',
    activeIcon: 'home',
  },
  {
    name: 'search', // `search.tsx`
    path: '/(app)/(customer)/search',
    icon: 'search-outline',
    activeIcon: 'search',
  },
  {
    name: 'reserves', // `reserves.tsx`
    path: '/(app)/(customer)/reserves',
    icon: 'calendar-outline',
    activeIcon: 'calendar',
  },
  {
    name: 'profile', // `profile.tsx`
    path: '/(app)/(customer)/profile',
    icon: 'person-outline',
    activeIcon: 'person',
  }
];

export const hairdresserTabs = [
    {
      name: 'profile', // Assumes app/(app)/(hairdresser)/profile.tsx
      path: '/(app)/(hairdresser)/profile',
      icon: 'person-outline',
      activeIcon: 'person',
    },
    {
      name: 'services', // Assumes app/(app)/(hairdresser)/services.tsx
      path: '/(app)/(hairdresser)/services',
      icon: 'cut-outline',
      activeIcon: 'cut',
    },
    {
      name: 'agenda', // Assumes app/(app)/(hairdresser)/agenda.tsx
      path: '/(app)/(hairdresser)/agenda',
      icon: 'calendar-clear-outline',
      activeIcon: 'calendar-clear',
    }
];