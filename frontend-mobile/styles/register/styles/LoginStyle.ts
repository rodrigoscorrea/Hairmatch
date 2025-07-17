import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
      padding: 20,
      alignItems: 'center',
    },
    logoContainer: {
      alignItems: 'center',
      marginTop: 60,
      marginBottom: 40,
    },
    logoText: {
      fontSize: 32,
      fontWeight: 'bold',
      color: '#FF7A00',
    },
    logoHighlight: {
      color: '#FF7A00',
    },
    scissorsText: {
      fontSize: 24,
    },
    formContainer: {
      width: '80%',
      maxWidth: 350,
    },
    inputContainer: {
      marginBottom: 20,
    },
    inputError: {
    borderWidth: 1.5,
    borderColor: 'purple',
  },
    inputLabel: {
      fontSize: 14,
      color: '#333',
      marginBottom: 5,
    },
    input: {
      backgroundColor: '#FFFFFF',
      borderRadius: 8,
      padding: 12,
      //marginBottom: 20,
      borderWidth: 0.2,
      borderColor: '#828282',
      fontSize: 16,
    },
    errorText:{
      color: 'purple',
      fontSize: 12,
      marginBottom: 10,
      marginLeft: 4,
      marginTop: 4,
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
    loginButton: {
      backgroundColor: colors.primary,
      borderRadius: 8,
      padding: 15,
      alignItems: 'center',
      marginTop: 10,
      width: '70%',
      alignSelf: 'center',
    },
    loginButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: 'bold',
    },
    signupContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      marginTop: 20,
    },
    signupText: {
      color: colors.textSecondary,
      fontSize: 15,
    },
    signupLink: {
      color: colors.primary,
      fontSize: 15,
      fontWeight: 'bold',
      textDecorationLine: 'underline',
    },
    modalOverlay: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      justifyContent: 'flex-end',
      alignItems: 'center',
    },
    modalContent: {
      backgroundColor: '#FFF',
      borderTopLeftRadius: 20,
      borderTopRightRadius: 20,
      padding: 25,
      width: '100%',
      alignItems: 'center',
    },
    modalTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      marginBottom: 12,
      color: '#333',
      textDecorationLine: 'underline',
    },
    modalText: {
      fontSize: 14,
      color: '#333',
      marginBottom: 20,
      textAlign: 'center',
    },
    modalButton: {
      backgroundColor: '#FF7A00',
      paddingVertical: 12,
      paddingHorizontal: 30,
      borderRadius: 8,
    },
    modalButtonText: {
      color: '#FFF',
      fontWeight: 'bold',
      fontSize: 16,
    },
  });
  