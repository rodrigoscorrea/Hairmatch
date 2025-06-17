import { StyleSheet, Dimensions, ViewStyle, TextStyle } from 'react-native';
import { colors } from '@/assets/colors';

const { width } = Dimensions.get('window');

interface Styles {
  container: ViewStyle;
  header: ViewStyle;
  tabContainer: ViewStyle;
  tab: ViewStyle;
  activeTab: ViewStyle;
  tabText: TextStyle;
  activeTabText: TextStyle;
  calendarHeader: ViewStyle;
  calendarHeaderText: TextStyle;
  dayHeaderText: TextStyle;
  dayNamesContainer: ViewStyle;
  dayName: TextStyle;
  calendarContainer: ViewStyle;
  eventBlock: ViewStyle;
  eventText: TextStyle;
  eventCell: ViewStyle;
  calendarCell: ViewStyle;
  calendarCellText: TextStyle;
  bottomNavigation: ViewStyle;
  navItem: ViewStyle;
  navIcon: ViewStyle;
  activeNavIcon: ViewStyle;
}

export const calendarTheme = {
  palette: {
    primary: {
      main: colors.details_purple, 
      contrastText: '#fff',
    },
    gray: {
      100: '#f5f5f5', // Fundos claros
      200: '#e0e0e0', // Bordas
      300: '#bdbdbd',
      500: '#757575', // Textos secundários
      800: '#424242', // Textos principais
    },
  },
};

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.background,
    //paddingTop: 10,
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingTop: 8,
    backgroundColor: colors.secondary,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    //borderRadius: 8,
    marginHorizontal: 4,
  },
  activeTab: {
    borderBottomColor: colors.details_purple,
    borderBottomWidth: 2,
  },
  tabText: {
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  activeTabText: {
    color: '#000',
    fontWeight: '600',
  },
  calendarHeader: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.background,
  },
  calendarHeaderText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#000',
  },
  dayHeaderText: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  dayNamesContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: colors.background,
  },
  dayName: {
    flex: 1,
    textAlign: 'center',
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  calendarContainer: {
    flex: 1,
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 12,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
  },
  eventBlock: {
    borderRadius: 4,
    padding: 4,
    marginVertical: 1,
    minHeight: 20,
    justifyContent: 'center',
  },
  eventText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  eventCell: {
    backgroundColor: '#9B7EBD',
    borderRadius: 4,
    padding: 2,
  },
  calendarCell: {
    borderWidth: 0.5,
    borderColor: '#e0e0e0',
  },
  calendarCellText: {
    fontSize: 16,
    color: '#000',
  },
  bottomNavigation: {
    flexDirection: 'row',
    backgroundColor: colors.background,
    paddingVertical: 12,
    paddingHorizontal: 16,
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  navItem: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 40,
    height: 40,
  },
  navIcon: {
    width: 24,
    height: 24,
    backgroundColor: '#ccc',
    borderRadius: 4,
  },
  activeNavIcon: {
    backgroundColor: '#9B7EBD',
  },
  agendaItem: {
    flexDirection: 'row',
    backgroundColor: colors.background,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.details_purple,
    padding: 15,
    marginHorizontal: 16,
    marginVertical: 6,
    elevation: 2,
    //shadowColor: '#000',
    /*shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,*/
  },
  dateContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 15,
    paddingRight: 15,
    borderRightWidth: 1,
    borderRightColor: '#9B7EBD',
  },
  dayText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#9B7EBD',
  },
  monthText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#A0A0A0',
  },
  detailsContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  titleText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  timeText: {
    fontSize: 14,
    color: '#555',
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
    color: '#A0A0A0',
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
  backButton: {
    backgroundColor: 'gray',
    padding: 10,
    borderRadius: 8
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold'
  },
});