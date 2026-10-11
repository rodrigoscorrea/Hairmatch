import { useCallback, useEffect, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { getAlerts } from '@/services/alert.service';
import { onAlertReceived } from '@/utils/push-registration';

// The menu shows "99+" from this many unread alerts on.
const BADGE_LIMIT = 100;

/**
 * The text of the unread counter of the "Notificações" menu item, or undefined to hide it: nothing unread,
 * not read yet, or the request failed (a counter is never worth an error, NOTIF-58).
 */
export const useUnreadAlertsCount = (): string | undefined => {
  const [count, setCount] = useState<number | null>(null);

  const refresh = useCallback(() => getAlerts().then((list) => list.unreadCount), []);

  // On every focus, so alerts read in the inbox or received meanwhile show when the user comes back.
  useFocusEffect(
    useCallback(() => {
      let active = true;
      refresh()
        .then((unread) => active && setCount(unread))
        .catch(() => active && setCount(null));
      return () => {
        active = false;
      };
    }, [refresh])
  );

  // And when a push arrives with the app open.
  useEffect(() => {
    let active = true;
    const stop = onAlertReceived(() => {
      refresh()
        .then((unread) => active && setCount(unread))
        .catch(() => active && setCount(null));
    });
    return () => {
      active = false;
      stop();
    };
  }, [refresh]);

  if (!count) return undefined;
  return count >= BADGE_LIMIT ? '99+' : String(count);
};
