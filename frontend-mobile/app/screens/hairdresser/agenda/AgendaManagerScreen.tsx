import React, {useState, useEffect} from 'react'
import { Text, View, TouchableOpacity, Alert, Modal, TextInput, Pressable, Platform } from 'react-native';
import { useBottomTab } from '@/app/contexts/BottomTabContext'
import BottomTabBar from '@/app/components/BottomBar'
import { Calendar} from 'react-native-big-calendar';
import DateTimePicker from '@react-native-community/datetimepicker';
import dayjs from 'dayjs';
import { createAgendaApointment, listAgendaByHairdresser } from '@/app/services/agenda.service';
import { styles } from './AgendaManagerStyles';

function AgendaManagerScreen() {
    const {hairdresser, setActiveTab} = useBottomTab();
    const [mode, setMode] = useState<any>("schedule");
    const [showPicker, setShowPicker] = useState<boolean>(false);
    const [pickerMode, setPickerMode] = useState<string>("start"); 
    const [modalVisible, setModalVisible] = useState<boolean>(false);
    const [selectedDate, setSelectedDate] = useState<any>(null);
    const [eventTitle, setEventTitle] = useState<string>("");
    const [startTime, setStartTime] = useState<any>(null);
    const [endTime, setEndTime] = useState<any>(null);
    const [editingEventId, setEditingEventId] = useState<any>(null);
    const [events, setEvents] = useState<any[]>([]);
    
    const onEventPress = (event: any) => {
        setEditingEventId(event.id);
        setEventTitle(event.title);
        setStartTime(new Date(event.start));
        setEndTime(new Date(event.end));
        setModalVisible(true);
    };

  useEffect(() => {

    const fetchAgendaEvents = async () => {
      try {
        const response = await listAgendaByHairdresser(hairdresser?.id);
        const converted = response.data.map((ev:any) => ({
          id: ev.id,
          title: ev.service.name,
          start: new Date(ev.start_time),
          end: new Date(ev.end_time),
        }));
        setEvents(converted);  
      } catch (error) {
        console.log('Error while fetching agenda events', error);
      }
    }
    fetchAgendaEvents();
  }, []);

  const createNewAgendaAppointment = async (event: any) => {
    try {
      console.log(event)
      await createAgendaApointment({
        hairdresser: event.hairdresser,
        service: event.service,
        start_time: event.start_time,
      });
      setEvents([...events, {
        id: Math.random().toString(),
        title: 'Outro',
        start: new Date(event.start_time),
        end: new Date(event.end_time),
      }]);
    } catch (error) {
      console.log('Error while creating agenda apointment', error);
    }
  }

    /* const onCellPress = (date: any) => {
        const base = dayjs(date).startOf("hour");
        setSelectedDate(base);
        setStartTime(base.toDate());
        setEndTime(base.add(30, "minutes").toDate());
        setEventTitle("corte");
        setEditingEventId(null);
        setModalVisible(true);
    }; */

    const onDayChange = (val: any) => {
        setMode(val);
    };

    const handleTimeChange = (event: any, selectedDate: any) => {
        if (selectedDate) {
          if (pickerMode === "start") {
              setStartTime(selectedDate);
          } else {
              setEndTime(selectedDate);
          }
        }
        setShowPicker(false);
    };

    /* const handleAddOrEditEvent = () => {
        if (!eventTitle.trim()) {
        Alert.alert("Erro", "Digite um título para o evento.");
        return;
        }
    
        if (!startTime || !endTime || dayjs(startTime).isAfter(endTime)) {
        Alert.alert("Erro", "Verifique os horários de início e fim.");
        return;
        }
    
        const hasConflict = events.some((ev: any) => {
          if (editingEventId && ev.id === editingEventId) return false;
      
          return (
              dayjs(startTime).isBefore(dayjs(ev.end)) &&
              dayjs(endTime).isAfter(dayjs(ev.start))
          );
        });
    
        if (hasConflict) {
          Alert.alert("Conflito", "Esse horário já está ocupado por outro evento.");
          return;
        }
    
        if (editingEventId) {
            setEvents((prev: any) =>
                prev.map((ev:any) =>
                ev.id === editingEventId
                    ? { ...ev, title: eventTitle, start: startTime, end: endTime }
                    : ev
                )
            );
        } else {
            const newEvent = {
                hairdresser: hairdresser?.id,
                service: 1,
                start_time: startTime,
                end_time: endTime
            };
            createNewAgendaAppointment(newEvent);
        }
    
        closeModal();
    }; */

    const handleCancelEvent = () => {
        if (editingEventId) {
          setEvents((prev: any) => prev.filter((ev:any) => ev.id !== editingEventId));
          closeModal();
        }
    };

    const closeModal = () => {
        setModalVisible(false);
        setEventTitle("");
        setStartTime(null);
        setEndTime(null);
        setEditingEventId(null);
    };

    const modeLabels: any = {
        day: "Dia",
        week: "Semana",
        month: "Mês",
        schedule: "Agenda",
    };

    useEffect(()=>{
        setActiveTab('AgendaManager')
    }, [])  

    return (
    <View style={{ flex: 1 }}>
      <View style={styles.viewstyle}>
        {["day", "week", "month", "schedule"].map((item) => (
          <TouchableOpacity
            key={item}
            style={[styles.button, mode === item ? styles.activecolor : styles.inactivecolor]}
            onPress={() => onDayChange(item)}
          >
            <Text style={styles.textstyle}>{modeLabels[item]}</Text>
          </TouchableOpacity>
        ))}
      </View>

      
      <Calendar
            events={events}
            date={new Date()}
            height={600}
            mode={mode}
            onPressEvent={onEventPress}
            locale="pt-br"
            minHour={10}
            maxHour={18}
            
          />
      <Modal
        visible={modalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={closeModal}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              Agendamento
            </Text>

            <Text style={styles.input}>{eventTitle}</Text>

            <Text style={styles.label}>Início: {startTime ? dayjs(startTime).format("HH:mm") : "--:--"}</Text>
            {/* <Pressable
              style={styles.selectButton}
              onPress={() => {
                setPickerMode("start");
                setShowPicker(true);
              }}
            >
              <Text style={styles.buttonText}>Selecionar Início</Text>
            </Pressable> */}

            <Text style={styles.label}>Fim: {endTime ? dayjs(endTime).format("HH:mm") : "--:--"}</Text>
            {/* <Pressable
              style={styles.selectButton}
              onPress={() => {
                setPickerMode("end");
                setShowPicker(true);
              }}
            >
              <Text style={styles.buttonText}>Selecionar Fim</Text>
            </Pressable> */}

            <View style={styles.modalButtons}>
              <Pressable style={styles.cancelButton} onPress={handleCancelEvent}>
                <Text style={styles.buttonText}>Cancelar</Text>
              </Pressable>
              <Pressable style={styles.backButton} onPress={closeModal}>
                <Text style={styles.buttonText}>Voltar</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      {showPicker && (
        <DateTimePicker
          value={pickerMode === "start" ? startTime || new Date() : endTime || new Date()}
          mode="time"
          is24Hour={true}
          display={Platform.OS === "ios" ? "spinner" : "default"}
          onChange={handleTimeChange}
        />
      )}
      <BottomTabBar/>
    </View>
  );
}

export default AgendaManagerScreen
