export const validatePassword = (password?: string): boolean => {
  if(!password) return false;

  const minLength = 8;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const isValidLength = password.length >= minLength;

  return hasUpperCase && hasLowerCase && hasNumber && isValidLength;
};

export const formatCPF = (value?: string): string => {
  if(!value) return '';

  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
};

export const formatCNPJ = (value?: string): string => {
  if (!value) return '';

  const digits = value.replace(/\D/g, '').slice(0, 14);
  if (digits.length <= 2) return digits;
  if (digits.length <= 5) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  if (digits.length <= 8) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
  if (digits.length <= 12) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
};

export const formatCEP = (value?: string): string => {
  if(!value) return '';

    return value
      .replace(/\D/g, '')                  
      .replace(/^(\d{5})(\d)/, '$1-$2')    
      .slice(0, 9);                        
  };

export const formatPhone = (value?: string): string => {
  if (!value) return '';

  const cleaned = value.replace(/\D/g, '').slice(0, 11);
  const { length } = cleaned;

  if (length > 10) {
    return cleaned.replace(/^(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  }

  return cleaned
    .replace(/^(\d{2})(\d)/, '($1) $2')
    .replace(/(\d{4})(\d)/, '$1-$2');
};
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
};

export const stripNonDigits = (value: string) => value.replace(/\D/g, '');

export const formatTimeInput = (value: string): string => {
  const digits = value.replace(/\D/g, '').slice(0, 4).padStart(4, '0');

  if (digits.length === 0) return '';

  let hour = parseInt(digits.slice(0, 2), 10);
  let minute = parseInt(digits.slice(2, 4), 10);

  // Limitar valores máximos válidos
  hour = Math.min(hour, 23);
  minute = Math.min(minute, 59);

  const formattedHour = hour.toString().padStart(2, '0');
  const formattedMinute = minute.toString().padStart(2, '0');

  return `${formattedHour}:${formattedMinute}`;
};

