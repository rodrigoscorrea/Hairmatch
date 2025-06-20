import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export const formatDate = (dateString: string | null) => {
    if(!dateString) return '';
    try {
      const localData = dateString.replace(/Z$/, '') // Remove 'Z' if present to avoid UTC issues
      const date = new Date(localData);
      return format(date, 'dd/MM/yyyy', { locale: ptBR });
    } catch (e) {
      return 'Invalid date';
    }
  };