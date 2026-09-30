import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';

// The API sends UTC instants ("...Z"); show them in the device's local time.
export const formatTime = (dateString: string) : string => {
  try {
    return dayjs(dateString).format("HH:mm[h]");
  } catch (e) {
    return 'Invalid hour';
  }
};
