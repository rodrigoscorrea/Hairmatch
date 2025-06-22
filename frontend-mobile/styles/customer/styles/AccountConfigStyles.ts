import { StyleSheet } from 'react-native';
import { colors } from '@/assets/colors';

export const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
        header: {
        flexDirection: 'row',
        alignItems: 'center',
        //paddingHorizontal: 20,
        paddingTop: 15,
        paddingBottom: 15,
        backgroundColor: colors.background,
    },
        backButton: {
        marginRight: 5,
        marginLeft:5
     },
    buttonTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#333',
    },
    headerTitle:{
        fontSize: 18,
        flex: 1,
        fontWeight: '600',
        color: '#333',
        textAlign: 'center'
    },
    profilePicContainer: {
      alignItems: 'center',
      marginVertical: 20,
    },
    profilePic: {
      width: 120,
      height: 120,
      borderRadius: 60,
      backgroundColor: '#FFE4C4', // Cor de fundo do círculo
      justifyContent: 'center',
      alignItems: 'center',
      borderWidth: 1,
      borderColor: '#ccc'
    },
    form: {
      paddingHorizontal: 20,
    },
    inputContainer: {
      marginBottom: 15,
    },
    saveButton: {
      backgroundColor: '#FF7A00', // Laranja
      padding: 15,
      borderRadius: 8,
      alignItems: 'center',
      margin: 20,
    },
    saveButtonText: {
      color: '#fff',
      fontSize: 18,
      fontWeight: 'bold',
    },
  });