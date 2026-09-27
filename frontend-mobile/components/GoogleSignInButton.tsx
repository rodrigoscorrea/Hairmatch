import React from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '@/assets/colors';

type GoogleSignInButtonProps = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
};

export const GoogleSignInButton = ({ label, onPress, disabled, loading }: GoogleSignInButtonProps) => {
  const isDisabled = !!disabled || !!loading;

  return (
    <TouchableOpacity
      style={[styles.button, isDisabled && styles.buttonDisabled]}
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: !!loading }}
    >
      <Ionicons name="logo-google" size={20} color={colors.textSecondary} />
      <Text style={styles.label}>{label}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.white,
    borderRadius: 8,
    borderWidth: 0.5,
    borderColor: '#828282',
    padding: 14,
    width: '100%',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 10,
  },
});
