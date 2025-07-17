import { colors } from "@/assets/colors";
import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  container: {
    padding: 20,
    backgroundColor: '#FFEFE2',
    flexGrow: 1,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    alignSelf: 'center',
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#FFF',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  textarea: {
    height: 100,
    textAlignVertical: 'top',
  },
  label: {
    fontWeight: '600',
    marginBottom: 6,
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  durationLabel: {
    marginLeft: 10,
    fontWeight: '600',
  },
  helperText: {
    fontSize: 12,
    color: '#555',
    marginBottom: 16,
  },
  toggleContainer: {
    flexDirection: 'row',
    borderRadius: 10,
    overflow: 'hidden',
    marginBottom: 10,
  },
  toggleButton: {
    flex: 1,
    padding: 10,
    alignItems: 'center',
    backgroundColor: '#F4D2B8',
  },
  activeToggle: {
    backgroundColor: '#FFF',
  },
  inactiveToggle: {
    backgroundColor: '#F4D2B8',
  },
  toggleText: {
    fontWeight: '600',
  },
  activeText: {
    color: '#000',
  },
  inactiveText: {
    color: '#888',
  },
  variationRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 10,
  },
  variationInput: {
    flex: 1,
    backgroundColor: '#FFF',
    padding: 10,
    borderRadius: 8,
  },
  valueInput: {
    width: 80,
    backgroundColor: '#FFF',
    padding: 10,
    borderRadius: 8,
  },
  addButton: {
    backgroundColor: '#FF8A00',
    padding: 10,
    borderRadius: 8,
    alignSelf: 'flex-start',
    marginBottom: 20,
  },
  addButtonText: {
    color: '#FFF',
    fontWeight: 'bold',
  },
  footerButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 16,
    backgroundColor: '#FFEFE2',
    borderTopWidth: 1,
    borderColor: '#ddd',
    gap: 16,
  },
  saveButton: {
    backgroundColor: colors.primary,
    padding: 14,
    borderRadius: 10,
    flex: 1,
    marginRight: 10,
    alignItems: 'center',
  },
  saveText: {
    color: colors.white,
    fontWeight: '600',
  },
  cancelButton: {
    backgroundColor: colors.background,
    borderWidth:1,
    borderColor: colors.details_purple,
    padding: 14,
    borderRadius: 10,
    flex: 1,
    alignItems: 'center',
  },
  cancelText: {
    color: colors.details_purple,
    fontWeight: '600',
  },
  inputError: {
    borderWidth: 1.5,
    borderColor: 'purple',
  },
});