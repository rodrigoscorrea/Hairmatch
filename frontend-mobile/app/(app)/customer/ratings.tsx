// app/(app)/customer/ratings.tsx
import React from 'react';
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { colors } from '@/assets/colors';
import { StarRating } from '@/components/StarRating/StarRating';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useReceivedRatings } from '@/hooks/customerHooks/useReceivedRatings';

dayjs.locale('pt-br');

export default function ReceivedRatingsScreen() {
  const { ratings, isLoaded, errorModal, closeError, handleGoBack } = useReceivedRatings();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity onPress={handleGoBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>‹ Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Avaliações recebidas</Text>
      </View>

      <FlatList
        data={ratings}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          isLoaded ? <Text style={styles.emptyText}>Você ainda não recebeu avaliações.</Text> : null
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <StarRating rating={item.rating} size={18} />
              <Text style={styles.date}>{dayjs(item.created_at).format('DD/MM/YYYY')}</Text>
            </View>
            {item.comment ? <Text style={styles.comment}>{item.comment}</Text> : null}
            {item.service_name ? <Text style={styles.detail}>Serviço: {item.service_name}</Text> : null}
            <Text style={styles.detail}>{item.hairdresser_name ?? 'Cabeleireiro removido'}</Text>
          </View>
        )}
      />

      <ErrorModal visible={errorModal.visible} message={errorModal.message} onClose={closeError} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
  },
  backButton: {
    paddingVertical: 6,
  },
  backButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.details_purple,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 8,
  },
  list: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginTop: 40,
    fontSize: 15,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    padding: 15,
    marginTop: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  date: {
    fontSize: 13,
    color: '#777',
  },
  comment: {
    fontSize: 15,
    color: '#333',
    marginTop: 10,
  },
  detail: {
    fontSize: 13,
    color: '#666',
    marginTop: 6,
  },
});
