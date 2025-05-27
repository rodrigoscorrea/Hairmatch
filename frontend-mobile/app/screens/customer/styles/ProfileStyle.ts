import { StyleSheet } from "react-native";
import { colors } from "@/assets/colors";

export const styles = StyleSheet.create({
    container: {
      display: 'flex',
      flexDirection: 'column',
      flex: 1,
      backgroundColor: colors.background,
      justifyContent: 'center',
      alignContent: 'center',
      alignItems: 'center'
    },
    wipImage: {
      width: 350,
      height:250
    }
})