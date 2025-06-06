import React, {useState, useEffect} from 'react'
import { StyleSheet, Text, View, TouchableOpacity, Alert, Modal, TextInput, Pressable, Platform } from 'react-native';
import { useBottomTab } from '@/app/contexts/BottomTabContext'
import BottomTabBar from '@/app/components/BottomBar'
import { Calendar} from 'react-native-big-calendar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DateTimePicker from '@react-native-community/datetimepicker';
import dayjs from 'dayjs';
import { listAgendaByHairdresser } from '@/app/services/agenda.service';
const STORAGE_KEY = "@calendar_events";
function AgendaManagerScreen() {
    const {hairdresser, setActiveTab} = useBottomTab();
    const [mode, setMode] = useState<any>("schedule");
    const [showPicker, setShowPicker] = useState<boolean>(false);
    const [pickerMode, setPickerMode] = useState<string>("start"); 
    const [displayMonth, setDisplayMonth] = useState<any>(new Date());
    const [modalVisible, setModalVisible] = useState<boolean>(false);
    const [selectedDate, setSelectedDate] = useState<any>(null);
    const [eventTitle, setEventTitle] = useState<string>("");
    const [startTime, setStartTime] = useState<any>(null);
    const [endTime, setEndTime] = useState<any>(null);
    const [editingEventId, setEditingEventId] = useState<any>(null);
    const [agendaEvents, setAgendaEvents] = useState<any>();
    const [events, setEvents] = useState<any[]>([]);
    
    const onEventPress = (event: any) => {
        setEditingEventId(event.id);
        setEventTitle(event.title);
        setStartTime(new Date(event.start));
        setEndTime(new Date(event.end));
        setModalVisible(true);
    };

    // Carregar eventos do AsyncStorage
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

    const onCellPress = (date: any) => {
        const base = dayjs(date).startOf("hour");
        setSelectedDate(base);
        setStartTime(base.toDate());
        setEndTime(base.add(30, "minutes").toDate());
        setEventTitle("corte");
        setEditingEventId(null);
        setModalVisible(true);
    };

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

    const handleAddOrEditEvent = () => {
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
                title: eventTitle,
                start: startTime,
                end: endTime,
            };
            setEvents((prev: any) => [...prev, newEvent]);
        }
    
        closeModal();
    };

    const handleDeleteEvent = () => {
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
            onPressCell={onCellPress}
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
              {editingEventId ? "Editar Evento" : "Novo Evento"}
            </Text>

            <TextInput
              style={styles.input}
              placeholder="Título do evento"
              value={eventTitle}
              onChangeText={setEventTitle}
            />

            <Text style={styles.label}>Início: {startTime ? dayjs(startTime).format("HH:mm") : "--:--"}</Text>
            <Pressable
              style={styles.selectButton}
              onPress={() => {
                setPickerMode("start");
                setShowPicker(true);
              }}
            >
              <Text style={styles.buttonText}>Selecionar Início</Text>
            </Pressable>

            <Text style={styles.label}>Fim: {endTime ? dayjs(endTime).format("HH:mm") : "--:--"}</Text>
            <Pressable
              style={styles.selectButton}
              onPress={() => {
                setPickerMode("end");
                setShowPicker(true);
              }}
            >
              <Text style={styles.buttonText}>Selecionar Fim</Text>
            </Pressable>

            <View style={styles.modalButtons}>
              <Pressable style={styles.confirmButton} onPress={handleAddOrEditEvent}>
                <Text style={styles.buttonText}>{editingEventId ? "Salvar" : "Adicionar"}</Text>
              </Pressable>
              {editingEventId && (
                <Pressable style={styles.deleteButton} onPress={handleDeleteEvent}>
                  <Text style={styles.buttonText}>Excluir</Text>
                </Pressable>
              )}
              <Pressable style={styles.cancelButton} onPress={closeModal}>
                <Text style={styles.buttonText}>Cancelar</Text>
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

const styles = StyleSheet.create({
  viewstyle: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginVertical: 16
  },
  button: {
    height: 30,
    width: 70,
    alignContent: "center",
    alignItems: "center",
    padding: 5,
    borderRadius: 10
  },
  textstyle: {
    color: "white",
    textAlign: "center",
    fontWeight: "700",
    textTransform: "capitalize"
  },
  activecolor: {
    backgroundColor: "green"
  },
  inactivecolor: {
    backgroundColor: "gray"
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  modalContent: {
    width: 300,
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 10
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 8,
    marginBottom: 10
  },
  label: {
    marginTop: 10,
    marginBottom: 5,
    fontWeight: '600'
  },
  selectButton: {
    backgroundColor: '#007AFF',
    padding: 10,
    borderRadius: 8,
    marginBottom: 10,
    alignItems: 'center'
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10
  },
  confirmButton: {
    backgroundColor: 'green',
    padding: 10,
    borderRadius: 8
  },
  deleteButton: {
    backgroundColor: 'red',
    padding: 10,
    borderRadius: 8
  },
  cancelButton: {
    backgroundColor: 'gray',
    padding: 10,
    borderRadius: 8
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold'
  },
  monthContainer: {
    alignItems: 'center',
    marginVertical: 10,
  },
  monthText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
});

export default AgendaManagerScreen
