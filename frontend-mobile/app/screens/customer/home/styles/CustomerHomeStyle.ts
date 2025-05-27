import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
      paddingTop: 20,
      paddingHorizontal: 5,
    },
    scrollContainer: {
      flex: 1,
      paddingTop: 20,
      paddingHorizontal: 5,
    },
    searchBar: {
      backgroundColor: colors.white,
      borderRadius: 10,
      padding: 10,
      fontSize: 16,
      borderColor: '#ccc',
      borderWidth: 1,
      marginBottom: 20,
    },
    section: {
      marginBottom: 20,
    },
    sectionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 10,
    },
    sectionTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      flex: 1,
    },
    arrow: {
      fontSize: 22,
      color: colors.black,
    },
    card: {
      backgroundColor: colors.secondary,
      borderRadius: 10,
      padding: 10,
      marginRight: 10,
      width: 180,
      height: 200
    },
    imageCard: {
      width: '100%',
      height: 100,
      borderRadius: 10,
    },
    nomeProfissional: {
      fontWeight: 'bold',
      marginTop: 5,
    },
    sobrenomeProfissional: {
      fontWeight: 'bold',
      marginTop: 5,
      marginLeft: 6
    },
    description: {
      fontSize: 12,
      color: colors.textSecondary,
    },
    circleItem: {
      alignItems: 'center',
      marginRight: 15,
    },
    circleImage: {
      width: 60,
      height: 60,
      borderRadius: 30,
      marginBottom: 5,
    },
    circleText: {
      fontSize: 12,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 20,
    },
  });
  