export type AlertKind =
  | 'reservation-created'
  | 'review-created'
  | 'review-updated'
  | 'review-deleted'
  | 'customer-rating-created'
  | 'customer-rating-updated'
  | 'customer-rating-deleted';

/** A notification kept for the logged user, whether or not a push reached the phone. */
export interface Alert {
  id: number;
  // A string the app does not know (a kind added by a newer backend) still renders; it just has no destination.
  kind: AlertKind | (string & {});
  title: string;
  body: string;
  // Ids of what the alert is about, e.g. { reservation_id }. Empty when the row is gone.
  data: Record<string, number>;
  read: boolean;
  created_at: string;
}

export interface AlertList {
  alerts: Alert[];
  unreadCount: number;
}

/** What a tap on a push carries: the alert it opened and its kind. */
export interface AlertTap {
  alertId: number;
  kind: string;
}
