import React from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, ScrollView, Alert, Modal, ActivityIndicator } from 'react-native';
import { useDescriptionForm } from '../../../hooks/authHooks/useDescription'; // Adjust path
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';


const DescriptionScreen = () => {
  const {
    isLoading,
    showAiDescriptionModal,
    setShowAiDescriptionModal,
    formData,
    handleResumeChange,
    handleRequestAiResume,
    handleFinish,
    errorModal,
    closeErrorModal,
    handleBack,
  } = useDescriptionForm();

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Descrição Profissional</Text>
      <Text style={styles.subtitle}>Esse texto será a descrição do seu perfil</Text>

      {isLoading ? (
        <>
          <ActivityIndicator size="large" />
        </>
      ):(
        <>
          <TextInput
            style={styles.textArea}
            placeholder="Insira aqui a sua descrição detalhada para que atraia mais clientes"
            placeholderTextColor="#aaa"
            multiline
            value={formData.resume}
            onChangeText={handleResumeChange}
          />
        </>
      )}

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.backButton} onPress={handleBack} disabled={isLoading}>
          <Text style={styles.backText}>Voltar</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishButton} onPress={handleFinish} disabled={isLoading}>
          <Text style={styles.finishText}>Finalizar</Text>
        </TouchableOpacity>
      </View>
      <Modal
        visible={showAiDescriptionModal}
        transparent
        animationType="fade"
      >
        <View style={styles.modalOverlay}>
            <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>Deseja incrementar sua descrição com IA?</Text>
            <Text style={styles.modalText}>
                Otimize sua descrição com o apoio da inteligência artificial! Com base nas informações que você fornecer, a IA irá gerar um texto mais atrativo, profissional e alinhado ao seu perfil.
                Basta inserir alguns detalhes e deixar que a IA faça o trabalho inicial. Você poderá editar o resultado como preferir.
            </Text>
            <View style={styles.modalButtonGroup}>
                <TouchableOpacity
                    style={styles.modalBackButton}
                    onPress={() => setShowAiDescriptionModal(false)}
                >
                    <Text style={styles.modalBackButtonText}>Pular</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={styles.modalAcceptButton}
                    onPress={handleRequestAiResume}
                >
                    <Text style={styles.modalAcceptButtonText}>Aceitar</Text>
                </TouchableOpacity>
            </View>
            </View>
        </View>
      </Modal>
      <ErrorModal
        visible={errorModal.visible}
        onClose={closeErrorModal}
        message={errorModal.message}
      />
    </ScrollView>
  );
};

export default DescriptionScreen;

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#FFEFE5',
    flexGrow: 1,
    justifyContent: 'flex-start',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 12,
    textAlign: 'center',
    color: '#555',
    marginBottom: 24,
  },
  textArea: {
    height: 200,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    textAlignVertical: 'top',
    borderColor: '#ddd',
    borderWidth: 1,
    fontSize: 14,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 30,
  },
  backButton: {
    backgroundColor: '#E5E0F8',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  finishButton: {
    backgroundColor: '#FF7A00',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  backText: {
    color: '#4B0082',
    fontWeight: '600',
  },
  finishText: {
    color: '#fff',
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContainer: {
    backgroundColor: '#FFECE3',
    borderRadius: 20,
    padding: 20,
    width: '100%',
    maxWidth: 320,
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 10,
    color: '#333',
  },
  modalText: {
    fontSize: 14,
    textAlign: 'center',
    color: '#555',
    marginBottom: 20,
  },
  modalButtonGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
  },
  modalBackButton: {
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderColor: '#9B59B6',
    borderWidth: 1,
    marginRight: 10,
    flex: 1,
    alignItems: 'center',
  },
  modalBackButtonText: {
    color: '#9B59B6',
    fontWeight: '500',
  },
  modalAcceptButton: {
    backgroundColor: '#FF6B00',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 20,
    flex: 1,
    alignItems: 'center',
  },
  modalAcceptButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
});
