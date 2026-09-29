import { UserInfo, UserRole } from '../models/User.types';

export const CUSTOMER_HOME = '/(app)/customer/home';
export const HAIRDRESSER_HOME = '/(app)/hairdresser/agenda';

// Landing screen of the logged user's role, or null while there is no user info.
export const homeRouteFor = (userInfo: UserInfo | null | undefined) => {
  if (userInfo?.customer?.user?.role === UserRole.CUSTOMER) return CUSTOMER_HOME;
  if (userInfo?.hairdresser?.user?.role === UserRole.HAIRDRESSER) return HAIRDRESSER_HOME;
  return null;
};
