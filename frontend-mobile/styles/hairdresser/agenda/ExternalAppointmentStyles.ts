import { StyleSheet } from 'react-native';
import { colors } from '@/assets/colors';

export const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  backButton: {
    position: 'absolute',
    left: 0,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  label: {
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 6,
  },
  calendar: {
    borderRadius: 10,
    overflow: 'hidden',
  },
  timeRow: {
    flexDirection: 'row',
    gap: 12,
  },
  timeColumn: {
    flex: 1,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.details_purple,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
    backgroundColor: colors.white,
  },
  chipSelected: {
    backgroundColor: colors.details_purple,
  },
  chipText: {
    color: colors.details_purple,
    fontWeight: '500',
  },
  chipTextSelected: {
    color: colors.white,
  },
  footerButtons: {
    flexDirection: 'row',
    marginTop: 24,
    gap: 16,
  },
  cancelButton: {
    backgroundColor: colors.background,
    borderWidth: 1,
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
  saveButton: {
    backgroundColor: colors.primary,
    padding: 14,
    borderRadius: 10,
    flex: 1,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveText: {
    color: colors.white,
    fontWeight: '600',
  },
});
