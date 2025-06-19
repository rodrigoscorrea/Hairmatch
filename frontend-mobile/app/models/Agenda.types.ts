export interface AgendaEvent {
    id: any; 
    title: string;
    start: Date;
    end: Date;
}
  
export type CalendarMode = 'month' | 'week' | 'day' | 'agenda';

export interface AgendaViewProps {
    events: AgendaEvent[];
    onEventPress: (event: AgendaEvent) => void;
}