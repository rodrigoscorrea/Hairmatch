import React, { useState, useEffect, useCallback } from 'react';
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
import { FontAwesome } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '@/app/_layout';
import { useRouter, useLocalSearchParams, router } from 'expo-router';
import { ReserveWithService } from '@/models/Reserve.types';
import { getReserveById } from '@/services/reserve.service';
import { createReview } from '@/services/review.service';

export const useReviewForm = () => {
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [image, setImage] = useState<any>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { userInfo } = useAuth();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [reserve, setReserve] = useState<ReserveWithService | null>(null);

  useEffect(() => {
    const fetchReserve = async () => {
      if (!id) return;
      setIsLoading(true);
      try {
        const response = await getReserveById(Number(id)); 
        setReserve(response.data);
        //console.log(response.data)
        //console.log(userInfo)
      } catch (error) {
        console.error("Failed to fetch reserve details:", error);
        Alert.alert("Erro", "Não foi possível carregar os detalhes do agendamento.");
      } finally {
        setIsLoading(false);
      }
    };
    fetchReserve();
  }, [id]);

  const handleGoBack = () => {
    router.push(`/(app)/(customer)/reserves/${id}`);
  }

  const handleImagePick = useCallback(async () => {
    // Request permission for media library access
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Sorry, we need camera roll permissions to make this work!');
      return;
    }

    // Launch the image library
    let result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });
    if (result.canceled) {
        return;
    }
    const imageAsset = result.assets[0];
    if (!result.canceled) {
      setImage(
        {
            uri: imageAsset.uri,
            type: imageAsset.mimeType || 'image/jpeg',
            name: imageAsset.fileName || `profile_${Date.now()}.jpg`
        }
      );
      setImagePreview(imageAsset.uri);
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (rating === 0) {
      Alert.alert('Incomplete', 'Please provide a star rating.');
      return;
    }

    setIsLoading(true);
    const formData = new FormData();

    formData.append('rating', isNaN(rating) ? Number(0).toString() : rating.toString());
    formData.append('comment', comment);
    formData.append('hairdresser', Number(reserve?.service.hairdresser.id).toString())
    formData.append('reserve', id);

    if (image) {
      if (Platform.OS === 'web') {
        image.name = image.name
        const response = await fetch(image.uri);
        const blob = await response.blob();
        formData.append('picture', blob, image.name);
      } else {
          const fileData = {
            uri: image.uri,
            name: image.name,
            type: image.type,
        };

        formData.append('picture', fileData as any);
      }
    }

    //Clean the forms
    setImagePreview(null);
    setComment('');
    setRating(0);
    setImage(null);

    try {      
      await createReview(formData);
      
      Alert.alert('Success!', 'Your review has been submitted successfully.');
      router.push(`/(app)/(customer)/reserves/${id}`);
    } catch (error) {
      console.error('Error submitting review:', error);
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [rating, comment, image, id]);

  return {
    rating,
    setRating,
    comment,
    setComment,
    image,
    imagePreview,
    handleImagePick,
    handleGoBack,
    handleSubmit,
    isLoading,
    reserve,
    userInfo
  };
};
