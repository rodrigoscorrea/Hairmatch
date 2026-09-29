import axios from 'axios';
import { API_BACKEND_URL } from '@/app/_layout';

// Contract of POST /api/auth/google (400/401/403/409 errors arrive as { error } in axios)
export type GoogleAuthResponse =
  | { status: 'authenticated' }
  | {
      status: 'signup_required';
      signup_token: string;
      prefill: { email: string; first_name: string; last_name: string };
    };

export const loginWithGoogle = async (idToken: string): Promise<GoogleAuthResponse> => {
  try {
    const response = await axios.post<GoogleAuthResponse>(
      `${API_BACKEND_URL}/api/auth/google`,
      { id_token: idToken },
      { withCredentials: true },
    );
    return response.data;
  } catch (error) {
    console.error("Error in loginWithGoogle:", error);
    throw error;
  }
};
