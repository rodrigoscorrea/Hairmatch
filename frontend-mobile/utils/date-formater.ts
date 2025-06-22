import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export const formatDate = (dateString: string | null) => {
  if (!dateString) return '';
  try {
    const date = parseISO(dateString); // ISO string como '2025-06-26'
    return format(date, 'dd/MM/yyyy', { locale: ptBR });
  } catch (e) {
    return 'Invalid date';
  }
};
