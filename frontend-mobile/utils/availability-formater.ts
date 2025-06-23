const weekdayTranslations = {
  monday: 'Segunda-feira',
  tuesday: 'Terça-feira',
  wednesday: 'Quarta-feira',
  thursday: 'Quinta-feira',
  friday: 'Sexta-feira',
  saturday: 'Sábado',
  sunday: 'Domingo'
};

const formatTime = (time: string): string => {
  if (!time) return '';
  const [hours, minutes] = time.split(':');
  const formattedHours = parseInt(hours, 10);

  if (minutes === '00') {
    return `${formattedHours}h`;
  }
  
  return `${formattedHours}:${minutes}h`;
};

export const formatAvailability = (availability: {
  weekday: string;
  start_time: string;
  end_time: string;
  break_start: string | null;
  break_end: string | null;
}) => {
  const translatedWeekday = weekdayTranslations[availability.weekday as keyof typeof weekdayTranslations] || availability.weekday;
  const formattedStartTime = formatTime(availability.start_time);
  const formattedEndTime = formatTime(availability.end_time);
  
  let timeRange = `${formattedStartTime} - ${formattedEndTime}`;
  
  return {
    weekday: translatedWeekday,
    timeRange
  };
};
