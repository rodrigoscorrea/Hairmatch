import type { Href } from 'expo-router';
import { UserInfo } from '@/models/User.types';
import { HAIRDRESSER_HOME } from '@/utils/routes';

// Plain `Href` casts: the typed routes are generated from the files of app/, so a screen that is new in the same
// change would not type-check yet.
export const CUSTOMER_NOTIFICATIONS = '/(app)/customer/notifications' as Href;
export const HAIRDRESSER_NOTIFICATIONS = '/(app)/hairdresser/profile/notifications' as Href;
export const HAIRDRESSER_REVIEWS = '/(app)/hairdresser/profile/reviews' as Href;

/** The inbox of the logged user's role, or null while there is no user info. */
export const inboxRoute = (userInfo: UserInfo | null | undefined): Href | null => {
  if (userInfo?.customer) return CUSTOMER_NOTIFICATIONS;
  if (userInfo?.hairdresser) return HAIRDRESSER_NOTIFICATIONS;
  return null;
};

/**
 * Where a tap on an alert goes, or null to stay on the inbox. A review that was created or edited opens the
 * reviews the hairdresser received; a removed one is no longer on that list, so `review-deleted` stays on the inbox.
 */
export const alertRoute = (kind: string): Href | null => {
  if (kind === 'reservation-created') return HAIRDRESSER_HOME;
  if (kind.startsWith('customer-rating-')) return '/(app)/customer/ratings';
  if (kind === 'review-created' || kind === 'review-updated') return HAIRDRESSER_REVIEWS;
  return null;
};

