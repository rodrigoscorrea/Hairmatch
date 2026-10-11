const pad = (value: number) => String(value).padStart(2, '0');

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

/** "agora", "há 5 min", "há 3 h" (same day), "ontem" or "dd/mm", on the clock of the device. */
export const relativeTime = (iso: string, now: Date = new Date()): string => {
  const moment = new Date(iso);
  const seconds = Math.max(0, Math.floor((now.getTime() - moment.getTime()) / 1000));
  if (seconds < 60) return 'agora';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `há ${minutes} min`;

  const days = Math.round((startOfDay(now) - startOfDay(moment)) / 86_400_000);
  if (days <= 0) return `há ${Math.floor(minutes / 60)} h`;
  if (days === 1) return 'ontem';
  return `${pad(moment.getDate())}/${pad(moment.getMonth() + 1)}`;
};
