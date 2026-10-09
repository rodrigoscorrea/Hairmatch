// The backend routes the session handling depends on. The refresh path lives here once, for the axios interceptor and the bootstrap.
export const REFRESH_PATH = '/api/auth/refresh';

// A 401 from these requests is a real answer (wrong password, no session to refresh, sign-up not allowed...), not an expired access token.
// `/api/users/me` and the other `/api/users/...` routes are not here: they need the refresh.
const REFRESH_EXCLUDED: { method: string; path: string }[] = [
  { method: 'post', path: '/api/auth/login' },
  { method: 'post', path: REFRESH_PATH },
  { method: 'post', path: '/api/auth/logout' },
  { method: 'post', path: '/api/auth/google' },
  { method: 'post', path: '/api/auth/email-confirmations' },
  { method: 'post', path: '/api/auth/confirmation-codes' },
  { method: 'post', path: '/api/users' },
];

// The path of a request URL, without host and without query string. The services pass both absolute and relative URLs.
export const pathnameOf = (url: string | undefined): string => {
  if (!url) return '';
  const withoutQuery = url.split(/[?#]/)[0];
  return withoutQuery.replace(/^[a-z][a-z0-9+.-]*:\/\/[^/]*/i, '');
};

// Exact comparison: a substring match would exclude `/api/users/me` because of `/api/users`.
export const isRefreshExcluded = (method: string | undefined, url: string | undefined): boolean => {
  const path = pathnameOf(url);
  const verb = (method ?? 'get').toLowerCase();
  return REFRESH_EXCLUDED.some((excluded) => excluded.method === verb && excluded.path === path);
};
