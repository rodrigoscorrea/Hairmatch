import React from 'react';
import { StyleSheet, TouchableOpacity, View } from 'react-native';
import { FontAwesome } from '@expo/vector-icons';

interface StarRatingProps {
  rating: number;
  // Without it the stars are read-only and ignore touches.
  onChange?: (rating: number) => void;
  size?: number;
}

const STARS = [1, 2, 3, 4, 5];

export const StarRating: React.FC<StarRatingProps> = ({ rating, onChange, size = 32 }) => (
  <View style={styles.stars}>
    {STARS.map((star) => {
      const icon = (
        <FontAwesome
          name={star <= rating ? 'star' : 'star-o'}
          size={size}
          color={star <= rating ? '#FFC107' : '#CCCCCC'}
          style={styles.star}
        />
      );
      return onChange ? (
        <TouchableOpacity key={star} onPress={() => onChange(star)}>
          {icon}
        </TouchableOpacity>
      ) : (
        <View key={star}>{icon}</View>
      );
    })}
  </View>
);

const styles = StyleSheet.create({
  stars: {
    flexDirection: 'row',
  },
  star: {
    marginHorizontal: 5,
  },
});
