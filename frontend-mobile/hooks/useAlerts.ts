import { useCallback, useRef, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { Alert } from '@/models/Alert.types';
import { getAlerts, markAlertRead, markAllAlertsRead } from '@/services/alert.service';
import { problemMessage } from '@/utils/api-problem';
import { alertRoute } from '@/utils/alert-routes';

export const useAlerts = () => {
  const router = useRouter();

  const [alerts, setAlerts] = useState<Alert[]>([]);
  // The unread alerts of all of them, not only of the 50 listed.
  const [unreadCount, setUnreadCount] = useState(0);
  // Only a successful fetch shows the empty message; a failure shows the error modal instead.
  const [isLoaded, setIsLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [errorModal, setErrorModal] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

  // Read again on every focus, so what was read elsewhere (or arrived meanwhile) shows when the user comes back.
  useFocusEffect(
    useCallback(() => {
      let active = true;
      getAlerts()
        .then((list) => {
          if (!active) return;
          // An update in flight owns the list.
          if (!busyRef.current) {
            setAlerts(list.alerts);
            setUnreadCount(list.unreadCount);
          }
          setIsLoaded(true);
        })
        .catch((error) => {
          if (!active) return;
          setIsLoaded(false);
          setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível carregar suas notificações.') });
        });
      return () => {
        active = false;
      };
    }, [])
  );

  // The list changes at once; a failed request puts it back as it was and says so.
  const update = async (change: () => void, request: () => Promise<unknown>): Promise<boolean> => {
    if (busyRef.current) return false;
    const before = { alerts, unreadCount };
    change();
    busyRef.current = true;
    setBusy(true);
    try {
      await request();
      return true;
    } catch (error) {
      setAlerts(before.alerts);
      setUnreadCount(before.unreadCount);
      setErrorModal({ visible: true, message: problemMessage(error, 'Não foi possível atualizar suas notificações.') });
      return false;
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const open = async (alert: Alert) => {
    const marked = await update(
      () => {
        if (alert.read) return;
        setAlerts((current) => current.map((item) => (item.id === alert.id ? { ...item, read: true } : item)));
        setUnreadCount((count) => Math.max(0, count - 1));
      },
      () => markAlertRead(alert.id, true)
    );
    if (!marked) return;
    // An alert without a destination (review-deleted) leaves the user on the inbox, with the alert read.
    const destination = alertRoute(alert.kind);
    if (destination) router.push(destination);
  };

  const markAll = () =>
    update(
      () => {
        setAlerts((current) => current.map((item) => ({ ...item, read: true })));
        setUnreadCount(0);
      },
      markAllAlertsRead
    );

  return {
    alerts,
    unreadCount,
    isLoaded,
    busy,
    open,
    markAll,
    errorModal,
    closeError: () => setErrorModal({ visible: false, message: '' }),
  };
};
