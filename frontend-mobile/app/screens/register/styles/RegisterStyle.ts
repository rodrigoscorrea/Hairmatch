import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
      alignItems: 'center',
      padding: 20,
    },
    backButton: {
      position: 'absolute',
      top: 20,
      left: 20,
      zIndex: 1,
    },
    backButtonText: {
      fontSize: 32,
      color: colors.black,
    },
    title: {
      fontSize: 32,
      fontWeight: 'bold',
      color: colors.textPrimary,
      marginTop: 40,
    },
    subtitle: {
      fontSize: 20,
      marginVertical: 10,
    },
    toggleContainer: {
      flexDirection: 'row',
      backgroundColor: '#F8DFF2',
      borderRadius: 20,
      marginVertical: 15,
    },
    toggleButton: {
      paddingVertical: 8,
      paddingHorizontal: 20,
      borderRadius: 20,
    },
    toggleButtonSelected: {
      backgroundColor: '#8e44ad',  
    },
    toggleButtonText: {
      color: '#555',
      fontWeight: '600',
    },
    toggleButtonTextSelected: {
      color: 'white',
      fontWeight: '700',
    },
    profilePicture: {
      width: 100,
      height: 100,
      borderRadius: 50,
      borderWidth: 1,
      borderColor: '#000000',
      justifyContent: 'center',
      alignItems: 'center',
      marginVertical: 15,
    },
    profileIcon: {
      width: 40,
      height: 40,
      tintColor: '#000', 
    },
    row: {
      flexDirection: 'row',
      width: '100%',
    },
    input: {
      backgroundColor: 'white',
      width: '100%',
      borderRadius: 10,
      paddingHorizontal: 15,
      paddingVertical: 12,
      marginVertical: 5,
    },
    passwordContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: 'white',
      borderRadius: 10,
      width: '100%',
      marginVertical: 5,
      position: 'relative', 
      paddingHorizontal: 15, 
    },
    inputInner: {
      flex: 1, 
      paddingVertical: 12, 
      fontSize: 16,
      color: '#333',
      paddingRight: 40, 
    },
    eyeIconAbsolute: {
      position: 'absolute',
      right: 15,
      paddingVertical: 5, 
    },
    button: {
      backgroundColor: colors.primary,
      borderRadius: 10,
      marginTop: 20,
      width: '100%',
      padding: 15,
      alignItems: 'center',
    },
    buttonText: {
      color: 'white',
      fontWeight: '700',
      fontSize: 16,
    },
  });