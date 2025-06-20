import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFEEDD', // cor clara parecida com a da imagem
    paddingTop: 20,
    paddingHorizontal: 16,
  },
  scrollContainer: {
    flex: 1,
    paddingTop: 20,
    paddingHorizontal: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  profile: {
    flexDirection: 'row',
    marginVertical: 16,
    alignItems: 'center',
  },
  profileImage: {
    width: 70,
    height: 70,
    borderRadius: 35,
    marginRight: 12,
  },
  profileText: {
    flex: 1,
  },
  name: {
    fontSize: 20,
    fontWeight: '600',
  },
  location: {
    fontSize: 12,
    color: '#555',
  },
  rating: {
    marginTop: 4,
    fontSize: 14,
    color: '#000',
  },
  bio: {
    fontSize: 13,
    color: '#333',
    marginBottom: 10,
  },
  more: {
    color: '#A85E49',
    fontWeight: 'bold',
  },
  sectionTitle: {
    fontWeight: 'bold',
    marginVertical: 10,
    fontSize: 16,
  },
  gallery: {
    flexDirection: 'row',
    gap: 8,
  },
  galleryImage: {
    width: 100,
    height: 100,
    borderRadius: 12,
    marginRight: 8,
  },
  techniques: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginVertical: 12,
  },
  techTag: {
    backgroundColor: '#FFD6C7',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  techText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#FFFFFF'
  },
  card: {
    borderWidth: 1,
    borderColor: '#FFA366',
    borderRadius: 16,
    padding: 12,
    paddingLeft: 16,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFEFE8',
  },
  cardText: {
    fontWeight: '600',
    fontSize: 14,
  },
  arrowButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#FF7A00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  availabilityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  weekday: {
    fontWeight: 'bold'
  },
  timeRange: {
    color: '#666'
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8, // React Native doesn’t support `gap` natively; use margin instead if needed
    marginTop: 8,
  },
  techCard: {
    backgroundColor: '#FF8822',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
    margin: 4,
  },
});
