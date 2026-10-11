import React, { useState } from 'react';
import { FlatList, Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { GalleryPhoto } from '@/models/Gallery.types';
import { PhotoViewer } from '@/components/PhotoViewer';

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

      <PhotoViewer uri={opened?.image ?? null} onClose={() => setOpened(null)} />
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
});
