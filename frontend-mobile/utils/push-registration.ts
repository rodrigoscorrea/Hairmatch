import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { AlertTap } from '@/models/Alert.types';
import { deletePushDevice, registerPushDevice } from '@/services/push-device.service';

// Everything that touches expo-notifications lives here and in push-registration.web.ts, which does nothing:
// the web has no push, so its bundle never imports the native module (NOTIF-18). Only Android is registered.
// Push is a courtesy, never a reason to show an error: every failure below is swallowed (NOTIF-16).

// Must match `defaultChannel` of the plugin in app.json and the `channel_id` the backend sends.
const CHANNEL_ID = 'default';

// While the app is open the push shows as a banner too.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

// The id that removes this phone again. In memory only: the POST repeats at every session, so it never has to survive a restart.
let deviceId: number | null = null;
// The POST in flight, so a logout right after a login waits for the id instead of leaving the phone registered.
let pending: Promise<void> = Promise.resolve();

const register = (token: string): Promise<void> => {
  pending = registerPushDevice(token)
    .then((id) => {
      deviceId = id;
    })
    .catch(() => {});
  return pending;
};

/** Asks for the permission once and registers the phone. Never throws. */
export async function registerForPush(): Promise<void> {
  try {
    if (Platform.OS !== 'android') return;
    // The channel comes first: Android 13 only shows the permission prompt once the app has one.
    await Notifications.setNotificationChannelAsync(CHANNEL_ID, {
      name: 'Notificações',
      importance: Notifications.AndroidImportance.HIGH,
    });
    let { status } = await Notifications.getPermissionsAsync();
    // Asked once: after a "no" the status is denied and the app leaves it to the system settings (NOTIF-15).
    if (status === 'undetermined') {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== 'granted') return;

    const token = await Notifications.getDevicePushTokenAsync();
    await register(String(token.data));
  } catch {
    // No Play Services, no google-services.json in the build, or no network: the inbox still works.
  }
}

/** Registers the new token when the system changes it. Returns the function that stops listening. */
export function onPushTokenChange(): () => void {
  if (Platform.OS !== 'android') return () => {};
  const subscription = Notifications.addPushTokenListener((token) => {
    void register(String(token.data));
  });
  return () => subscription.remove();
}

/** Removes this phone from the logged user before the logout. Never throws. */
export async function unregisterForPush(): Promise<void> {
  try {
    await pending;
    const id = deviceId;
    deviceId = null;
    if (id !== null) await deletePushDevice(id);
  } catch {
    // The logout goes on: the next account that logs in on this phone takes the token over (NOTIF-03).
  }
}

// Where the backend data comes in depends on the app state: `content.data` normally, the raw message otherwise (risk R4).
const readTap = (response: Notifications.NotificationResponse): AlertTap | null => {
  const request = response.notification.request;
  const trigger = request.trigger as { remoteMessage?: { data?: Record<string, unknown> } } | null;
  const data = (request.content.data as Record<string, unknown> | undefined) ?? trigger?.remoteMessage?.data ?? {};
  const alertId = Number(data.alert_id);
  if (!Number.isInteger(alertId)) return null;
  return { alertId, kind: String(data.kind ?? '') };
};

/**
 * Calls the handler for each tap on a push, and once for the tap that opened the app from closed (NOTIF-74).
 * Returns the function that stops listening.
 */
export function onAlertTap(handler: (tap: AlertTap) => void): () => void {
  if (Platform.OS !== 'android') return () => {};
  const handle = (response: Notifications.NotificationResponse) => {
    const tap = readTap(response);
    // Handled once: the last response would come back to the next screen that asks for it.
    Notifications.clearLastNotificationResponse();
    if (tap) handler(tap);
  };
  const subscription = Notifications.addNotificationResponseReceivedListener(handle);
  const last = Notifications.getLastNotificationResponse();
  if (last) handle(last);
  return () => subscription.remove();
}

/** Calls the handler when a push arrives with the app open. Returns the function that stops listening. */
export function onAlertReceived(handler: () => void): () => void {
  if (Platform.OS !== 'android') return () => {};
  const subscription = Notifications.addNotificationReceivedListener(() => handler());
  return () => subscription.remove();
}

/** Forgets the tap that opened the app without a session, so it does not open an alert after the next login (NOTIF-76). */
export function discardPendingAlertTap(): void {
  if (Platform.OS !== 'android') return;
  Notifications.clearLastNotificationResponse();
}
