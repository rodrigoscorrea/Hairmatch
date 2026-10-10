import React, { useState, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Image,
  ScrollView,
  Alert,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {styles} from '../../../../styles/customer/styles/ReviewStyles';
import { FontAwesome } from '@expo/vector-icons';
import { useReviewForm } from '@/hooks/customerHooks/useReviewForm';
import { StarRating } from '@/components/StarRating/StarRating';
import { ErrorModal } from '@/components/modals/ErrorModal/ErrorModal';

export default function ReviewScreen() {
  const {
    rating,
    setRating,
    comment,
    setComment,
    existing,
    queued,
    canAddPicture,
    isEditing,
    pickPictures,
    removeExisting,
    removeQueued,
    handleSubmit,
    handleGoBack,
    isLoading,
    isSubmitting,
    modal,
    closeModal,
  } = useReviewForm();

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>{isEditing ? 'Editar Avaliação' : 'Avaliar Atendimento'}</Text>
        <Text style={styles.subtitle}>Você pode enviar sua avaliação até 31/12/2025</Text>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Como foi seu atendimento?</Text>
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
            placeholder="Compartilhe sua experiência, elogios ou sugestões..."
            value={comment}
            onChangeText={setComment}
            textAlignVertical="top"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Envie fotos do resultado</Text>
          <View style={styles.thumbGrid}>
            {existing.map(picture => (
              <View key={`existing-${picture.id}`} style={styles.thumb}>
                <Image source={{ uri: picture.url }} style={styles.thumbImage} />
                <TouchableOpacity
                  style={styles.thumbRemove}
                  onPress={() => removeExisting(picture.id)}
                  accessibilityLabel="Remover foto"
                >
                  <FontAwesome name="times" size={14} color="#FFFFFF" />
                </TouchableOpacity>
              </View>
            ))}
            {queued.map((picture, index) => (
              <View key={`queued-${picture.uri}-${index}`} style={styles.thumb}>
                <Image source={{ uri: picture.uri }} style={styles.thumbImage} />
                <TouchableOpacity
                  style={styles.thumbRemove}
                  onPress={() => removeQueued(index)}
                  accessibilityLabel="Remover foto"
                >
                  <FontAwesome name="times" size={14} color="#FFFFFF" />
                </TouchableOpacity>
              </View>
            ))}
            {canAddPicture && (
              <TouchableOpacity style={styles.addPicture} onPress={pickPictures} accessibilityLabel="Adicionar foto">
                <FontAwesome name="camera" size={32} color="#888" />
              </TouchableOpacity>
            )}
          </View>
        </View>

        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.backButton} onPress={() => handleGoBack()}>
            <Text style={styles.backButtonText}>Voltar</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.submitButton, (isLoading || isSubmitting) && styles.disabledButton]} 
            onPress={handleSubmit}
            disabled={isLoading || isSubmitting}
          >
            <Text style={styles.submitButtonText}>{isSubmitting ? 'Enviando...' : 'Enviar'}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <ErrorModal visible={modal.visible} title={modal.title} message={modal.message} onClose={closeModal} />
    </SafeAreaView>
  );
};