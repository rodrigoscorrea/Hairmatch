import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flexGrow:1,
      padding: 16,
      backgroundColor: colors.background,
    },
    titleContainer: {
      display: 'flex',
      flexDirection: 'row',
      justifyContent: 'space-between',
      width: "100%"
    },
    clockIconContainer: {
      display: 'flex',
      flexDirection: 'row',
      alignContent: 'center',
      marginTop: 2
    },
    clockIcon:{
      marginTop: 5
    },
    title: {
      fontSize: 22,
      fontWeight: 'bold',
    },
    description: {
      fontSize: 14,
      marginTop: 6,
      marginBottom: 12,
      color: '#333',
    },
    sectionTitle: {
      fontWeight: 'bold',
      fontSize: 16,
      marginTop: 20,
    },
    option: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingVertical: 10,
      borderBottomWidth: 1,
      borderColor: '#eee',
    },
    optionText: {
      fontSize: 16,
    },
    check: {
      fontSize: 16,
      color: '#f08000',
    },
    date: {
      fontSize: 16,
      color: '#555',
      paddingVertical: 10,
      borderBottomWidth: 1,
      borderColor: '#eee',
    },
    grid: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      marginTop: 12,
      gap: 10,
    },
    selectedTimeSlot: {
      width: '22%',
      padding: 10,
      borderWidth: 1,
      borderColor: '#4E2F5D',
      backgroundColor: colors.primary,
      borderRadius: 8,
      alignItems: 'center',
    },
    timeSlot: {
      width: '22%',
      padding: 10,
      borderWidth: 1,
      borderColor: '#4E2F5D',
      backgroundColor: '#F5F5F5',
      borderRadius: 8,
      alignItems: 'center',
    },
    selectedTimeText: {
      fontSize: 14,
      color: 'white'
    },
    timeText: {
      fontSize: 14,
      color: 'black'
    },
    button: {
      backgroundColor: colors.primary,
      paddingVertical: 14,
      borderRadius: 10,
      marginTop: 30,
      alignItems: 'center',
    },
    buttonText: {
      color: 'white',
      fontWeight: 'bold',
      fontSize: 16,
    },
    monthHeader: {
      width: '100%',
      paddingVertical: 10,
      paddingHorizontal: 15,
      backgroundColor: '#f0f0f0',
      borderBottomWidth: 1,
      borderBottomColor: '#ddd',
    },
    monthText: {
      fontSize: 18,
      fontWeight: 'bold',
      textAlign: 'center',
      marginBottom: 5,
    },
    monthNavigation: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingHorizontal: 10,
    },
    modalOverlay: {
      flex: 1,
      backgroundColor: 'rgba(0,0,0,0.5)',
      justifyContent: 'center',
      alignItems: 'center',
      padding: 20,
    },
    modalContainer: {
      backgroundColor: colors.secondary,
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
      color: colors.textPrimary
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
      backgroundColor: colors.white,
      borderRadius: 10,
      paddingVertical: 10,
      paddingHorizontal: 20,
      borderColor: colors.details_purple,
      borderWidth: 1,
      marginRight: 10,
      flex: 1,
      alignItems: 'center',
    },
    modalBackButtonText: {
      color: colors.details_purple,
      fontWeight: '500',
    },
    modalAcceptButton: {
      backgroundColor: colors.primary,
      borderRadius: 10,
      paddingVertical: 10,
      paddingHorizontal: 20,
      flex: 1,
      alignItems: 'center',
    },
    modalAcceptButtonText: {
      color: colors.white,
      fontWeight: '600',
    },
  });
  