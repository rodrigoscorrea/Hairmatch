import React, { useState } from 'react';
import { FlatList, Image, Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { GalleryPhoto } from '@/models/Gallery.types';

interface Props {
  photos: GalleryPhoto[];
}

/** The "Galeria" section of a hairdresser profile: a strip of thumbnails that open full screen. Nothing without photos. */
export const GalleryStrip: React.FC<Props> = ({ photos }) => {
  const [opened, setOpened] = useState<GalleryPhoto | null>(null);

  if (photos.length === 0) return null;

  return (
    <View>
      <Text style={styles.sectionTitle}>Galeria</Text>
      <FlatList
        data={photos}
        keyExtractor={(photo) => String(photo.id)}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.gallery}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => setOpened(item)} accessibilityRole="button" accessibilityLabel="Abrir foto">
            <Image source={{ uri: item.image }} style={styles.thumbnail} />
          </TouchableOpacity>
        )}
      />

      <Modal visible={opened !== null} transparent animationType="fade" onRequestClose={() => setOpened(null)}>
        <View style={styles.viewer}>
          {opened && <Image source={{ uri: opened.image }} style={styles.fullImage} resizeMode="contain" />}
          <TouchableOpacity
            style={styles.closeButton}
            onPress={() => setOpened(null)}
            accessibilityRole="button"
            accessibilityLabel="Fechar foto"
          >
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  sectionTitle: {
    fontWeight: 'bold',
    marginVertical: 10,
    fontSize: 16,
  },
  gallery: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  thumbnail: {
    width: 100,
    height: 100,
    borderRadius: 12,
    marginRight: 8,
  },
  viewer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.92)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fullImage: {
    width: '100%',
    height: '100%',
  },
  closeButton: {
    position: 'absolute',
    top: 48,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
