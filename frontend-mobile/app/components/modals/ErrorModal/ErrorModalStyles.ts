import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.42)',
    justifyContent: 'flex-end', // Push modal to the bottom
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFECE3',
    padding: 25,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    width: '100%',
    alignItems: 'center',
  },

  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  modalText: {
    fontSize: 16,
    marginBottom: 20,
    textAlign: 'center',
  },
  modalButton: {
    backgroundColor: '#FF6B00',
    paddingVertical: 10,
    paddingHorizontal: 25,
    borderRadius: 10,
  },
  modalButtonText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 16,
  },
});
 //path app/components