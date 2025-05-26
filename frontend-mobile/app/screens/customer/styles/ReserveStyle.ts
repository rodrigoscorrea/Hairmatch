import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    content: {
      flex: 1,
      padding: 16,
      paddingTop: 60, // Extra padding at the top
    },
    headerText: {
      fontSize: 24,
      fontWeight: 'bold',
      marginBottom: 20,
      textAlign: 'center',
      color: colors.textPrimary,
    },
    loader: {
      flex: 1,
      justifyContent: 'center',
    },
    reservesContainer: {
      flex: 1,
    },
    reserveCard: {
      backgroundColor: colors.secondary,
      borderRadius: 16,
      padding: 16,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    hairdresserInfoContainer: {
      flexDirection: 'row',
      marginBottom: 12,
    },
    profileCircle: {
      width: 50,
      height: 50,
      borderRadius: 25,
      backgroundColor: colors.textSecondary, // Gray circle for profile placeholder
      marginRight: 12,
    },
    hairdresserDetailsContainer: {
      flex: 1,
      justifyContent: 'center',
    },
    hairdresserFirstName: {
      fontSize: 16,
      fontWeight: 'bold',
      color: colors.textPrimary,
      marginBottom: 4,
    },
    hairdresserLastName: {
      fontSize: 16,
      fontWeight: 'bold',
      color: colors.textPrimary,
      marginBottom: 4,
      marginLeft: 4
    },
    reserveDetailText: {
      fontSize: 14,
      color: colors.textSecondary,
      marginBottom: 2,
    },
    spacer: {
      color: '#999',
    },
    statusContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      marginTop: 4,
    },
    statusLabel: {
      fontSize: 14,
      color: '#555',
      marginRight: 4,
    },
    statusValue: {
      fontSize: 14,
      fontWeight: '600',
    },
    moreInfoButton: {
      backgroundColor: colors.primary,
      borderRadius: 8,
      padding: 12,
      alignItems: 'center',
      marginTop: 8,
    },
    moreInfoButtonText: {
      color: colors.white,
      fontWeight: '600',
      fontSize: 14,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    emptyText: {
      fontSize: 16,
      color: '#666',
      textAlign: 'center',
    },
  });