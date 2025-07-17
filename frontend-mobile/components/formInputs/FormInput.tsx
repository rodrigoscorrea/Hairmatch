import React from 'react';
import { TextInput, TextInputProps, View, StyleSheet } from 'react-native';
import { styles as globalStyles } from '../../styles/register/styles/RegisterStyle';

interface FormInputProps extends TextInputProps {
  isError?: boolean;
  containerStyle?: object;
}

export const FormInput: React.FC<FormInputProps> = ({ isError, style, containerStyle, ...props }) => {
  return (
    <View style={containerStyle}>
        <TextInput
          style={[globalStyles.input, isError && globalStyles.inputError, style]}
          placeholderTextColor="#888"
          {...props}
        />
    </View>
  );
};