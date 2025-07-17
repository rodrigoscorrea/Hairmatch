import React, { useState, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Image,
  ScrollView,
  SafeAreaView,
  Alert,
  Platform,
} from 'react-native';
import {styles} from '../../../../styles/customer/styles/ReviewStyles';
import { FontAwesome } from '@expo/vector-icons';
import { useReviewForm } from '@/hooks/customerHooks/useReviewForm';
import { router } from 'expo-router';

export default function ReviewScreen() {
  const {
    rating,
    setRating,
    comment,
    setComment,
    image,
    imagePreview,
    handleImagePick,
    handleSubmit,
    handleGoBack,
    isLoading,
    reserve,
    userInfo
  } = useReviewForm();

  // Component to render the star rating selector
  const StarRating = () => (
    <View style={styles.starContainer}>
      <Text style={styles.ratingLabel}>Ruim</Text>
      <View style={styles.stars}>
        {[1, 2, 3, 4, 5].map((star) => (
          <TouchableOpacity key={star} onPress={() => setRating(star)}>
            <FontAwesome
              name={star <= rating ? 'star' : 'star-o'}
              size={32}
              color={star <= rating ? '#FFC107' : '#CCCCCC'}
              style={styles.star}
            />
          </TouchableOpacity>
        ))}
      </View>
      <Text style={styles.ratingLabel}>Ótimo</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Avaliar Atendimento</Text>
        <Text style={styles.subtitle}>Você pode enviar sua avaliação até 31/12/2025</Text>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Como foi seu atendimento?</Text>
          <StarRating />
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
          <Text style={styles.sectionTitle}>Envie uma foto do resultado</Text>
          <TouchableOpacity style={styles.imagePicker} onPress={handleImagePick}>
            {imagePreview ? (
              <Image source={{ uri: imagePreview }} style={styles.previewImage} />
            ) : (
              <View style={styles.imagePickerContent}>
                <FontAwesome name="camera" size={40} color="#888" />
              </View>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.backButton} onPress={() => handleGoBack()}>
            <Text style={styles.backButtonText}>Voltar</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.submitButton, isLoading && styles.disabledButton]} 
            onPress={handleSubmit}
            disabled={isLoading}
          >
            <Text style={styles.submitButtonText}>{isLoading ? 'Enviando...' : 'Enviar'}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};