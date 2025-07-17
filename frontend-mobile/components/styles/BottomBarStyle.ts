import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      flexDirection: 'row',
      backgroundColor: colors.background,
      height: 60,
      borderTopWidth: 1,
      borderTopColor: '#e0e0e0',
      justifyContent: 'space-around',
      alignItems: 'center',
    },
    tabItem: {
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
    },
    tabText: {
      fontSize: 10,
      marginTop: 3,
      color: colors.textSecondary,
    },
    activeTabText: {
      color: colors.black,
      fontWeight: 'bold',
    },
    activeIcon:{
      color: colors.primary,
    },
    inactiveIcon:{
      color: colors.black
    }
  });
  