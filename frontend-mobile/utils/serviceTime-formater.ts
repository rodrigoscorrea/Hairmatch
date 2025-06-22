export const serviceTimeFormater = (minutes?: number) => {
    if (!minutes) return '';
    if (!minutes && minutes !== 0) return '0h 00min';
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    // Format remaining minutes to have leading zero if less than 10
    const formattedMinutes = remainingMinutes < 10 ? `0${remainingMinutes}` : remainingMinutes;
    
    if (hours === 0) {
      return `${formattedMinutes}min`;
    } else if (remainingMinutes === 0) {
      return `${hours}h`;
    } else {
      return `${hours}h ${formattedMinutes}min`;
    }
  };