import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
export const formatTime = (dateString: string) : string => {
  try {
    return dayjs.utc(dateString).format("HH:mm[h]");;
    //return format(date, "HH:mm'h'", { locale: ptBR });
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
