import axiosInstance from './axios-instance';

// POST /api/auth/email-confirmations: 200 activates the account. The errors arrive as problem+json
// (invalid-confirmation-code, confirmation-code-expired, too-many-requests, auth-unavailable).
export const confirmEmail = async (email: string, code: string): Promise<void> => {
  try {
    await axiosInstance.post(
      '/api/auth/email-confirmations',
      { email, code },
      { withCredentials: true },
    );
  } catch (error) {
    // The code is a secret and is not logged: only the failure.
    console.error("Error in confirmEmail");
    throw error;
  }
};

// POST /api/auth/confirmation-codes: always 202, so the answer never tells whether the account exists.
export const resendConfirmationCode = async (email: string): Promise<void> => {
  try {
    await axiosInstance.post(
      '/api/auth/confirmation-codes',
      { email },
      { withCredentials: true },
    );
  } catch (error) {
    console.error("Error in resendConfirmationCode");
    throw error;
  }
};
