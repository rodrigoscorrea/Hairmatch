import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      backgroundColor: colors.secondary,
      borderRadius: 12,
      padding: 12,
      marginBottom: 8,
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    title: {
      fontWeight: '600',
      fontSize: 15,
    },
    content: {
      marginTop: 8,
    },
  });
  