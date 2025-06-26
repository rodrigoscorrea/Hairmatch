import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
export const formatTime = (dateString: string) : string => {
  try {
    const date = new Date(dateString);
    return format(date, "HH:mm'h'", { locale: ptBR });
  } catch (e) {
    return 'Invalid hour';
  }
};

export const formatDateTimeForAgenda = (date: string) : string => {
  try {
    const formatedDate =  date.replace(/Z$/, '');
    return formatedDate;
  } catch (error) {
    return '';
  }
}
