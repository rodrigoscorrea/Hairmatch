import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#FFF3ED', padding: 20 },
    title: { fontSize: 20, fontWeight: 'bold', textAlign: 'center', marginBottom: 20 },
    tabContainer: { flexDirection: 'row', justifyContent: 'center' },
    tab: {
      borderWidth: 1, borderColor: '#ccc', padding: 10, width: 140,
      borderRadius: 12, marginHorizontal: 5, backgroundColor: '#FFF'
    },
    activeTab: {
      backgroundColor: '#fce6d6', borderColor: '#fa944b'
    },
    tabText: { textAlign: 'center', color: '#666' },
    activeTabText: { color: '#fa944b', fontWeight: 'bold', textAlign: 'center' },
    timeContainer: { marginTop: 20 , margin:"auto" },
    label: { fontWeight: 'bold', marginBottom: 5 },
    input: {
      backgroundColor: '#fde4d2', padding: 10, borderRadius: 10,
      width: 100, textAlign: 'center', fontSize: 18
    },
    dayRow: {
      flexDirection: 'row', alignItems: 'center', marginBottom: 15
    },
    dayLabel: { marginLeft: 10, width: 100 },
    timeInputs: { flexDirection: 'row', alignItems: 'center' },
    smallInput: {
      backgroundColor: '#fde4d2', padding: 5, borderRadius: 10,
      width: 60, textAlign: 'center'
    },
    buttonRow: {
      flexDirection: 'row', justifyContent: 'space-between',
      marginTop: 30, paddingHorizontal: 10
    },
    cancelButton: {
      backgroundColor: '#e5e4f4', padding: 12, borderRadius: 10, width: '40%', alignItems: 'center'
    },
    saveButton: {
      backgroundColor: '#fa944b', padding: 12, borderRadius: 10, width: '40%', alignItems: 'center'
    },
  });
  