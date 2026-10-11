// app/(app)/hairdresser/profile/reviews.tsx
import React, { useState } from 'react';
import { FlatList, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { colors } from '@/assets/colors';
import { PhotoViewer } from '@/components/PhotoViewer';
import { StarRating } from '@/components/StarRating/StarRating';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useHairdresserReviews } from '@/hooks/hairdresserHooks/useHairdresserReviews';

dayjs.locale('pt-br');

// The stars have no half, so the number shows the fraction: "4" and "4,5".
const formatRating = (rating: number): string =>
  Number.isInteger(rating) ? String(rating) : rating.toFixed(1).replace('.', ',');

export default function HairdresserReviewsScreen() {
  const { reviews, isLoaded, errorModal, closeError, handleGoBack } = useHairdresserReviews();
  const [openedPhoto, setOpenedPhoto] = useState<string | null>(null);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity onPress={handleGoBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>‹ Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Minhas avaliações</Text>
      </View>

      <FlatList
        data={reviews}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          isLoaded ? <Text style={styles.emptyText}>Você ainda não recebeu avaliações.</Text> : null
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.customerName}>
              {item.customer.user.first_name} {item.customer.user.last_name}
            </Text>
            <View style={styles.cardHeader}>
              <View style={styles.ratingRow}>
                <StarRating rating={item.rating} size={18} />
                <Text style={styles.ratingValue}>{formatRating(item.rating)}</Text>
              </View>
              <Text style={styles.date}>{dayjs(item.created_at).format('DD/MM/YYYY')}</Text>
            </View>
            {item.comment?.trim() ? <Text style={styles.comment}>{item.comment}</Text> : null}
            {item.pictures.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.photos}>
                {item.pictures.map((picture) => (
                  <TouchableOpacity
                    key={picture.id}
                    onPress={() => setOpenedPhoto(picture.url)}
                    accessibilityRole="button"
                    accessibilityLabel="Abrir foto"
                  >
                    <Image source={{ uri: picture.url }} style={styles.thumbnail} />
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}
          </View>
        )}
      />

      <PhotoViewer uri={openedPhoto} onClose={() => setOpenedPhoto(null)} />
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
  customerName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 6,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  ratingValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
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
  photos: {
    gap: 8,
    marginTop: 12,
  },
  thumbnail: {
    width: 72,
    height: 72,
    borderRadius: 10,
  },
});
