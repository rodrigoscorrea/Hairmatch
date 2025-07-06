import { StyleSheet, Dimensions } from 'react-native';
import { colors } from '@/assets/colors';

const { width } = Dimensions.get('window');

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    //paddingHorizontal: 20,
    paddingTop: 15,
    paddingBottom: 15,
    backgroundColor: colors.background,
  },
  backButton: {
    marginRight: 5,
    marginLeft:5
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 10,
  },
  profileCard: {
    borderRadius: 12,
    padding: 10,
    marginBottom: 15,
    borderWidth: 2,
    borderColor: colors.primary,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 25,
    backgroundColor: '#E0E0E0',
    marginRight: 10,
  },
  profileInfo: {
    flex: 1,
  },
  nameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  name: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginRight: 10,
  },
  rating: {
    fontSize: 14,
    color: '#666',
  },
  detailRow: {
    flexDirection: 'row',
    marginBottom: 5,
  },
  detailLabel: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
    width: 60,
  },
  detailValue: {
    fontSize: 14,
    color: '#666',
    flex: 1,
  },
  infoCard: {
    borderRadius: 12,
    padding: 10,
    marginBottom: 15,
    borderWidth: 2,
    borderColor: colors.primary,
  },
  infoLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    marginLeft: 5,
  },
  infoValue: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginLeft: 5,
  },
  buttonContainer: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
    marginTop: 5,
    marginBottom: 20,
    paddingHorizontal: 10,
  },
  button: {
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    flex: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  cancelButton: {
    backgroundColor: colors.background,
    //padding: 14,
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
  evaluateButton: {
    backgroundColor: colors.primary,
    marginRight: 5,
  },
  cancelButtonText: {
    fontSize: 14,
    color: colors.details_purple,
    fontWeight: '500',
  },
  evaluateButtonText: {
    fontSize: 14,
    color: '#FFFFFF',
    fontWeight: '600',
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    paddingVertical: 15,
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  navItem: {
    alignItems: 'center',
  },
  navIndicator: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 3,
    backgroundColor: '#007AFF',
    marginHorizontal: 20,
  },
  disabledButton:{
    backgroundColor: colors.primary,
    opacity: 0.5,
  },
  disabledCancelButton:{
    backgroundColor: colors.background,
    borderColor: colors.details_purple,
    opacity: 0.5
  },
  disabledButtonText:{
    color: '#FFFFFF',
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalReserveInformations: {
    marginBottom: 25,
    fontWeight: 400,
    marginTop: 5
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
  reviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4, // Adjust spacing as needed
  },
  reviewTitleContainer: {
      flexDirection: 'row',
      alignItems: 'center',
  },
  reviewRatingText: {
      fontSize: 16,
      fontWeight: 'bold',
      marginLeft: 4,
      color: '#333',
  },
  reviewImage: {
      width: '100%',
      height: 180,
      borderRadius: 8,
      marginTop: 12,
  },
  imagePlaceholder: {
      width: '100%',
      height: 120,
      borderRadius: 8,
      marginTop: 12,
      backgroundColor: '#f0f0f0',
      justifyContent: 'center',
      alignItems: 'center',
  },

  // --- Styles for the Pop-up Menu ---
  popupOverlay: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.1)', // Slight overlay to indicate modal is active
  },
  popupMenu: {
      position: 'absolute',
      top: 300, // You may need to adjust this value based on your screen layout
      right: 25, // You may need to adjust this value
      backgroundColor: 'white',
      borderRadius: 8,
      paddingVertical: 5,
      elevation: 5,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.25,
      shadowRadius: 3.84,
  },
  popupMenuItem: {
      paddingHorizontal: 15,
      paddingVertical: 10,
  },
  popupMenuItemText: {
      fontSize: 16,
      color: '#333',
  },
});