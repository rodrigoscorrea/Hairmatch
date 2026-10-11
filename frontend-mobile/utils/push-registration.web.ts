// The web has no push: no permission, no token, no POST (NOTIF-18). Same exports as push-registration.ts, all inert,
// so the web bundle never loads expo-notifications. The inbox and its counter work the same.
import { AlertTap } from '@/models/Alert.types';

export async function registerForPush(): Promise<void> {}

export function onPushTokenChange(): () => void {
  return () => {};
}

export async function unregisterForPush(): Promise<void> {}

export function onAlertTap(_handler: (tap: AlertTap) => void): () => void {
  return () => {};
}

export function onAlertReceived(_handler: () => void): () => void {
  return () => {};
}

export function discardPendingAlertTap(): void {}
