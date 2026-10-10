// app/(app)/hairdresser/rate-customer/[reservationId].tsx
import React from 'react';
import { Text, View, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styles } from '@/styles/hairdresser/RateCustomerStyles';
import { StarRating } from '@/components/StarRating/StarRating';
import ConfirmationModal from '@/components/modals/confirmationModal/ConfirmationModal';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { COMMENT_MAX_LENGTH, useRateCustomer } from '@/hooks/hairdresserHooks/useRateCustomer';
import { formatDate } from '@/utils/date-formater';

export default function RateCustomerScreen() {
  const {
    customerName,
    reservation,
    rating,
    setRating,
    comment,
    setComment,
    confirmVisible,
    openConfirm,
    closeConfirm,
    submit,
    isSubmitting,
    errorModal,
    closeError,
    goToAgenda,
    isEditing,
  } = useRateCustomer();

  const submitDisabled = rating === 0 || isSubmitting;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>{isEditing ? 'Editar Avaliação' : 'Avaliar Cliente'}</Text>
        <Text style={styles.customerName}>{customerName}</Text>
        <Text style={styles.subtitle}>
          {reservation ? `${reservation.service.name} · ${formatDate(reservation.start_time)}` : ''}
        </Text>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Como foi o atendimento deste cliente?</Text>
          <View style={styles.starContainer}>
            <Text style={styles.ratingLabel}>Ruim</Text>
            <StarRating rating={rating} onChange={setRating} />
            <Text style={styles.ratingLabel}>Ótimo</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Gostaria de deixar algum comentário?</Text>
          <TextInput
            style={styles.textInput}
            multiline
            numberOfLines={5}
            maxLength={COMMENT_MAX_LENGTH}
            placeholder="Conte como foi o atendimento (opcional)"
            value={comment}
            onChangeText={setComment}
            textAlignVertical="top"
          />
          <Text style={styles.counter}>{comment.length}/{COMMENT_MAX_LENGTH}</Text>
        </View>

        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.backButton} onPress={goToAgenda}>
            <Text style={styles.backButtonText}>Voltar</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.submitButton, submitDisabled && styles.disabledButton]}
            onPress={openConfirm}
            disabled={submitDisabled}
          >
            <Text style={styles.submitButtonText}>{isSubmitting ? 'Enviando...' : isEditing ? 'Salvar alterações' : 'Enviar avaliação'}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      <ConfirmationModal
        visible={confirmVisible}
        title={isEditing ? 'Salvar alterações?' : 'Enviar avaliação?'}
        description={
          isEditing
            ? 'Salvar as alterações da avaliação?'
            : 'Você poderá editar ou excluir a avaliação depois.'
        }
        confirmText={isEditing ? 'Salvar' : 'Enviar'}
        onConfirm={submit}
        onCancel={closeConfirm}
      />
      <ErrorModal visible={errorModal.visible} message={errorModal.message} onClose={closeError} />
    </SafeAreaView>
  );
}
