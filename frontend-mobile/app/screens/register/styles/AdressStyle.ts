import { colors } from '@/assets/colors';
import { StyleSheet } from 'react-native';

export const styles = StyleSheet.create({
  container: {
    flexGrow: 1, 
    backgroundColor: colors.background,
    alignItems: 'center',
    padding: 20,
    justifyContent: 'space-between', 
  },
  header: {
    marginTop: 70, 
    marginBottom: 10,
    alignItems: 'center',
  },
  form: {
    width: '100%',
    flex: 1,
    justifyContent: 'center', 
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: colors.textSecondary,
  },
  subtitle: {
    fontSize: 20,
    marginVertical: 10,
    color: '#555',
    textAlign: 'center',
  },
  row: {
    flexDirection: 'row',
    width: '100%',
  },
  input: {
    backgroundColor: 'white',
    width: '100%',
    borderRadius: 10,
    paddingHorizontal: 15,
    paddingVertical: 12,
    marginVertical: 5,
  },
  inputError: {
    borderWidth: 1.5,
    borderColor: 'purple',
  },
  buttonContainer: {
    flexDirection: 'row',
    marginTop: 80, 
    width: '100%',
    justifyContent: 'space-between',
  },
  backButton: {
    backgroundColor: '#FFFFFF',
    padding: 14,
    borderRadius: 8,
    borderColor: colors.details_purple,
    borderWidth:1,
    flex: 1,
    marginRight: 8,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  backButtonText: {
    color: colors.details_purple,
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    padding: 15,
    alignItems: 'center',
    flex: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  buttonText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 16,
  },
});