import React from 'react';
import { Modal, View, Text, TouchableOpacity } from 'react-native';
import {styles} from './ConfirmationModalStyles';

interface Props {
  visible: boolean;
  title: string;
  description: string;
  confirmText: string;
  onConfirm: () => void;
  onCancel?: () => void;
}

const ConfirmationModal: React.FC<Props> = ({
  visible,
  title,
  description,
  confirmText,
  onConfirm,
  onCancel,
}) => {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
    >
      <View style={styles.overlay}>
        <View style={styles.modalContainer}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.description}>{description}</Text>

          <View style={styles.buttonContainer}>
            <TouchableOpacity style={styles.cancelButton} onPress={onCancel}>
              <Text style={styles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.confirmButton} onPress={onConfirm}>
              <Text style={styles.confirmText}>{confirmText}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

export default ConfirmationModal;
