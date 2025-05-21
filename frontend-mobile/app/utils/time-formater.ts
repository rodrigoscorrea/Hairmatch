import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export const formatTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return format(date, 'HH\'h\'', { locale: ptBR }); // Format as "15h"
    } catch (e) {
      return 'Invalid hour';
    }
};