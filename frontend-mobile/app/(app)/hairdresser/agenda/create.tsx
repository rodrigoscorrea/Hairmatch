// app/(app)/hairdresser/agenda/create.tsx
import React from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { ptBR } from '@/utils/locale-calendar';
import { serviceTimeFormater } from '@/utils/serviceTime-formater';
import { FormInput } from '@/components/formInputs/FormInput';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useExternalAppointmentForm } from '@/hooks/hairdresserHooks/useExternalAppointmentForm';
import { styles } from '@/styles/hairdresser/agenda/ExternalAppointmentStyles';
import { colors } from '@/assets/colors';

LocaleConfig.locales['pt-br'] = ptBR;
LocaleConfig.defaultLocale = 'pt-br';

export default function ExternalAppointmentScreen() {
  const {
    today,
    date, setDate,
    startTime, handleStartTimeChange, handleStartTimeBlur,
    endTime, setEndTime, handleEndTimeBlur,
    services,
    serviceId, handleSelectService,
    title, setTitle,
    isSaving,
    handleSave,
    handleCancel,
    errorModal,
    closeErrorModal,
  } = useExternalAppointmentForm();

  const chips = [
    { id: null, label: 'Sem serviço' },
    ...services.map((service) => ({
      id: service.id,
      label: `${service.name} (${serviceTimeFormater(service.duration)})`,
    })),
  ];

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.headerContainer}>
          <TouchableOpacity onPress={handleCancel} style={styles.backButton}>
            <Ionicons name="chevron-back" size={26} color="#333" />
          </TouchableOpacity>
          <Text style={styles.title}>Atendimento externo</Text>
        </View>

        <Text style={styles.label}>Data</Text>
        <Calendar
          style={styles.calendar}
          hideExtraDays
          minDate={today}
          current={date}
          markedDates={{ [date]: { selected: true } }}
          onDayPress={(day: { dateString: string }) => setDate(day.dateString)}
          theme={{
            arrowColor: colors.primary,
            todayTextColor: colors.primary,
            selectedDayBackgroundColor: colors.primary,
            selectedDayTextColor: colors.white,
          }}
        />

        <View style={styles.timeRow}>
          <View style={styles.timeColumn}>
            <Text style={styles.label}>Início</Text>
            <FormInput
              placeholder="HH:mm"
              keyboardType="numeric"
              maxLength={5}
              value={startTime}
              onChangeText={handleStartTimeChange}
              onBlur={handleStartTimeBlur}
            />
          </View>
          <View style={styles.timeColumn}>
            <Text style={styles.label}>Término</Text>
            <FormInput
              placeholder="HH:mm"
              keyboardType="numeric"
              maxLength={5}
              value={endTime}
              onChangeText={setEndTime}
              onBlur={handleEndTimeBlur}
            />
          </View>
        </View>

        <Text style={styles.label}>Serviço</Text>
        <View style={styles.chipRow}>
          {chips.map((chip) => {
            const selected = chip.id === serviceId;
            return (
              <TouchableOpacity
                key={chip.id ?? 'none'}
                style={[styles.chip, selected && styles.chipSelected]}
                onPress={() => handleSelectService(chip.id)}
              >
                <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{chip.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.label}>Título</Text>
        <FormInput
          placeholder="Ex.: Cliente do WhatsApp"
          maxLength={100}
          value={title}
          onChangeText={setTitle}
        />

        <View style={styles.footerButtons}>
          <TouchableOpacity style={styles.cancelButton} onPress={handleCancel}>
            <Text style={styles.cancelText}>Cancelar</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.saveButton, isSaving && styles.saveButtonDisabled]}
            onPress={handleSave}
            disabled={isSaving}
          >
            <Text style={styles.saveText}>Salvar</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <ErrorModal visible={errorModal.visible} message={errorModal.message} onClose={closeErrorModal} />
    </View>
  );
}
