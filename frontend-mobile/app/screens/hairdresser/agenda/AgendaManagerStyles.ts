import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  viewstyle: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginVertical: 16
  },
  button: {
    height: 30,
    width: 70,
    alignContent: "center",
    alignItems: "center",
    padding: 5,
    borderRadius: 10
  },
  textstyle: {
    color: "white",
    textAlign: "center",
    fontWeight: "700",
    textTransform: "capitalize"
  },
  activecolor: {
    backgroundColor: "green"
  },
  inactivecolor: {
    backgroundColor: "gray"
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  modalContent: {
    width: 300,
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 10
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 8,
    marginBottom: 10
  },
  label: {
    marginTop: 10,
    marginBottom: 5,
    fontWeight: '600'
  },
  selectButton: {
    backgroundColor: '#007AFF',
    padding: 10,
    borderRadius: 8,
    marginBottom: 10,
    alignItems: 'center'
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10
  },
  cancelButton: {
    backgroundColor: 'red',
    padding: 10,
    borderRadius: 8
  },
  deleteButton: {
    backgroundColor: 'red',
    padding: 10,
    borderRadius: 8
  },
  backButton: {
    backgroundColor: 'gray',
    padding: 10,
    borderRadius: 8
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold'
  },
  monthContainer: {
    alignItems: 'center',
    marginVertical: 10,
  },
  monthText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
});