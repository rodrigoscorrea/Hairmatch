import { useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import { useAuth } from '@/app/_layout';
import { markAlertRead } from '@/services/alert.service';
import { toApiProblem } from '@/utils/api-problem';
import { alertRoute, inboxRoute } from '@/utils/alert-routes';
import { onAlertTap, onPushTokenChange, registerForPush } from '@/utils/push-registration';

/**
 * Ties push to the session: registers the phone while the user is logged in and opens the alert a tap on a push is about.
 * Mounted by the (app) layout and active only with a session (NOTIF-76: without one the login opens instead).
 */
export function usePushNotifications() {
  const router = useRouter();
  const { userInfo, userToken } = useAuth();
  // The tap handler is set once; the ref gives it the inbox of the role without listening again.
  const inbox = useRef(inboxRoute(userInfo));
  inbox.current = inboxRoute(userInfo);

  useEffect(() => {
    if (!userToken) return;
    void registerForPush();
    const stopTokenChanges = onPushTokenChange();
    const stopTaps = onAlertTap(async ({ alertId, kind }) => {
      try {
        await markAlertRead(alertId, true);
      } catch (error) {
        // A 401 is the session handling's to deal with. Any other failure, a 404 (an alert of another account) included,
        // leaves the user on the inbox, which says what the alerts really are (NOTIF-75).
        if (toApiProblem(error)?.status !== 401 && inbox.current) router.push(inbox.current);
        return;
      }
      const destination = alertRoute(kind) ?? inbox.current;
      if (destination) router.push(destination);
    });
    return () => {
      stopTokenChanges();
      stopTaps();
    };
  }, [userToken]);
}
