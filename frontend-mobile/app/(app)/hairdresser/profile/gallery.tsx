import React from 'react';
import { ActivityIndicator, FlatList, Image, StyleSheet, Text, TouchableOpacity, View, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '@/assets/colors';
import ConfirmationModal from '@/components/modals/confirmationModal/ConfirmationModal';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';
import { useGalleryManager } from '@/hooks/hairdresserHooks/useGalleryManager';
import { GALLERY_MAX_PHOTOS } from '@/models/Gallery.types';

const COLUMNS = 3;
const GAP = 8;
const PADDING = 16;
const MAX_CONTENT_WIDTH = 600;

export default function HairdresserGalleryScreen() {
  const {
    photos,
    loading,
    count,
    canAdd,
    busy,
    progress,
    pendingRemoval,
    modal,
    pickAndUpload,
    requestRemove,
    confirmRemove,
    cancelRemove,
    closeModal,
    handleBack,
  } = useGalleryManager();
  const { width } = useWindowDimensions();
  const cell = Math.floor((Math.min(width, MAX_CONTENT_WIDTH) - PADDING * 2 - GAP * (COLUMNS - 1)) / COLUMNS);
  const full = count >= GALLERY_MAX_PHOTOS;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={handleBack} accessibilityRole="button" accessibilityLabel="Voltar">
          <Ionicons name="arrow-back" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.title}>Minha galeria</Text>
        <Text style={styles.counter}>
          {count}/{GALLERY_MAX_PHOTOS}
        </Text>
      </View>

      <TouchableOpacity
        style={[styles.addButton, !canAdd && styles.addButtonDisabled]}
        onPress={pickAndUpload}
        disabled={!canAdd}
        accessibilityRole="button"
      >
        <Ionicons name="add" size={18} color="#fff" />
        <Text style={styles.addButtonText}>Adicionar fotos</Text>
      </TouchableOpacity>
      {progress ? (
        <Text style={styles.status}>
          Enviando {progress.current} de {progress.total}
        </Text>
      ) : (
        full && <Text style={styles.status}>Limite de 30 fotos atingido.</Text>
      )}

      {loading ? (
        <ActivityIndicator style={styles.loading} />
      ) : (
        <FlatList
          data={photos}
          keyExtractor={(photo) => String(photo.id)}
          numColumns={COLUMNS}
          columnWrapperStyle={{ gap: GAP }}
          contentContainerStyle={{ gap: GAP, paddingBottom: PADDING }}
          ListEmptyComponent={<Text style={styles.empty}>Você ainda não adicionou fotos.</Text>}
          renderItem={({ item }) => (
            <View style={{ width: cell, height: cell }}>
              <Image source={{ uri: item.image }} style={styles.photo} resizeMode="cover" />
              <TouchableOpacity
                style={[styles.removeButton, busy && styles.removeButtonDisabled]}
                onPress={() => requestRemove(item)}
                disabled={busy}
                accessibilityRole="button"
                accessibilityLabel="Remover foto"
              >
                <Ionicons name="trash-outline" size={16} color="#fff" />
              </TouchableOpacity>
            </View>
          )}
        />
      )}

      <ConfirmationModal
        visible={pendingRemoval !== null}
        title="Remover esta foto da galeria?"
        description="A foto sai da sua galeria e do seu perfil. Essa ação não pode ser desfeita."
        confirmText="Remover"
        onConfirm={confirmRemove}
        onCancel={cancelRemove}
      />
      <ErrorModal visible={modal.visible} message={modal.message} onClose={closeModal} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingTop: 20,
    paddingHorizontal: PADDING,
    width: '100%',
    maxWidth: MAX_CONTENT_WIDTH,
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
  },
  counter: {
    fontSize: 14,
    color: colors.textSecondary,
    minWidth: 40,
    textAlign: 'right',
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: colors.primary,
    borderRadius: 16,
    paddingVertical: 12,
  },
  addButtonDisabled: {
    opacity: 0.5,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  status: {
    marginTop: 8,
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  loading: {
    marginTop: 24,
  },
  empty: {
    marginTop: 32,
    textAlign: 'center',
    color: colors.textPlaceholder,
  },
  photo: {
    width: '100%',
    height: '100%',
    borderRadius: 12,
  },
  removeButton: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeButtonDisabled: {
    opacity: 0.4,
  },
});
