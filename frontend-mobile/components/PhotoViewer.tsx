import React from 'react';
import { Image, Modal, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  /** The photo to show full screen; the viewer is hidden while this is null. */
  uri: string | null;
  onClose: () => void;
}

/** A photo in full screen over a dark backdrop, with a button to close it. */
export const PhotoViewer: React.FC<Props> = ({ uri, onClose }) => (
  <Modal visible={uri !== null} transparent animationType="fade" onRequestClose={onClose}>
    <View style={styles.viewer}>
      {uri && <Image source={{ uri }} style={styles.fullImage} resizeMode="contain" />}
      <TouchableOpacity
        style={styles.closeButton}
        onPress={onClose}
        accessibilityRole="button"
        accessibilityLabel="Fechar foto"
      >
        <Ionicons name="close" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  </Modal>
);

const styles = StyleSheet.create({
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
