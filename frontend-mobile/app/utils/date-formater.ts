import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export const formatDate = (dateString: string | null) => {
    if(!dateString) return '';
    try {
      const date = new Date(dateString);
      return format(date, 'dd/MM/yyyy', { locale: ptBR });
    } catch (e) {
      return 'Invalid date';
    }
  };