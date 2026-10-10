// app/(app)/customer/favorites.tsx
import React from 'react';
import { FlatList, Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Entypo, Ionicons } from '@expo/vector-icons';
import { colors } from '@/assets/colors';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useFavoriteHairdressers } from '@/hooks/customerHooks/useFavoriteHairdressers';

export default function FavoriteHairdressersScreen() {
  const { favorites, isLoaded, removing, handleRemove, handleOpen, handleGoBack, errorModal, closeError } =
    useFavoriteHairdressers();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <TouchableOpacity onPress={handleGoBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>‹ Voltar</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Favoritos</Text>
      </View>

      <FlatList
        data={favorites}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          isLoaded ? <Text style={styles.emptyText}>Você ainda não tem cabeleireiros favoritos.</Text> : null
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            {/* The profile area and the heart are siblings, so the heart never opens the profile. */}
            <TouchableOpacity style={styles.openArea} onPress={() => handleOpen(item.id)}>
              <Image
                source={
                  item.user.profile_picture
                    ? { uri: item.user.profile_picture }
                    : require('../../../assets/images/profile_picture_placeholder.png')
                }
                style={styles.avatar}
              />
              <View style={styles.info}>
                <Text style={styles.name}>{`${item.user.first_name} ${item.user.last_name}`}</Text>
                <View style={styles.ratingRow}>
                  <Ionicons name="star" size={16} color="#FFB800" />
                  <Text style={styles.ratingText}>{item.user.rating?.toFixed(1) ?? '5.0'}</Text>
                </View>
                <View style={styles.locationRow}>
                  <Entypo name="location-pin" size={16} color="#7B3F00" />
                  <Text style={styles.address} numberOfLines={1}>
                    {item.user.neighborhood}, {item.user.city}
                  </Text>
                </View>
              </View>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.heartButton}
              onPress={() => handleRemove(item.id)}
              disabled={removing}
              accessibilityLabel="Remover dos favoritos"
            >
              <Ionicons name="heart" size={24} color="#D32F2F" />
            </TouchableOpacity>
          </View>
        )}
      />

      <ErrorModal visible={errorModal.visible} message={errorModal.message} onClose={closeError} />
    </SafeAreaView>
  );
}

// The card is the one of the search results (SearchStyle), with a heart where the search has an arrow.
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
    flexDirection: 'row',
    backgroundColor: '#FFDCC0',
    borderRadius: 16,
    padding: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  openArea: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#D9D9D9',
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  name: {
    fontWeight: 'bold',
    fontSize: 16,
    marginBottom: 2,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  ratingText: {
    marginLeft: 4,
    fontSize: 14,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  address: {
    marginLeft: 4,
    fontSize: 12,
    color: '#555',
    flex: 1,
  },
  heartButton: {
    padding: 8,
  },
});
