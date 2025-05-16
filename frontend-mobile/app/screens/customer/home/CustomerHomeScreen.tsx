// App.js
import React from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  FlatList,
  Image,
  ScrollView,
  TouchableOpacity,
} from 'react-native';

const dataParaVoce = [1, 2, 3];
const dataCachos = [1, 2, 3, 4];
const dataColoracao = [1, 2, 3, 4];

const CustomerHomeScreen = () => {
  const renderParaVoceItem = () => (
    <View style={styles.card}>
      <Image
        source={{ uri: 'https://via.placeholder.com/100x100?text=Img' }}
        style={styles.imageCard}
      />
      <Text style={styles.nomeProfissional}>Nome do Profissional</Text>
      <Text style={styles.description}>
        Lorem Ipsum is simply dummy text of the printing and typesetting industry.
      </Text>
    </View>
  );

  const renderCircleItem = () => (
    <View style={styles.circleItem}>
      <Image
        source={{ uri: 'https://via.placeholder.com/60x60?text=Img' }}
        style={styles.circleImage}
      />
      <Text style={styles.circleText}>Title</Text>
    </View>
  );

  return (
    <ScrollView style={styles.container}>
      <TextInput
        placeholder="Buscar no HairMatch"
        style={styles.searchBar}
        placeholderTextColor="#999"
      />

      {/* Seção Para Você */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Para Você</Text>
          <Text style={styles.arrow}>›</Text>
        </View>
        <FlatList
          data={dataParaVoce}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(_, index) => `para-voce-${index}`}
          renderItem={renderParaVoceItem}
        />
      </View>

      {/* Seção Cachos */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Cachos</Text>
          <Text style={styles.arrow}>›</Text>
        </View>
        <FlatList
          data={dataCachos}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(_, index) => `cachos-${index}`}
          renderItem={renderCircleItem}
        />
      </View>

      {/* Seção Coloração */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Coloração</Text>
          <Text style={styles.arrow}>›</Text>
        </View>
        <FlatList
          data={dataColoracao}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(_, index) => `coloracao-${index}`}
          renderItem={renderCircleItem}
        />
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFEEDD', // cor clara parecida com a da imagem
    paddingTop: 50,
    paddingHorizontal: 16,
  },
  searchBar: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 10,
    fontSize: 16,
    borderColor: '#ccc',
    borderWidth: 1,
    marginBottom: 20,
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    flex: 1,
  },
  arrow: {
    fontSize: 22,
    color: '#FF6600',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 10,
    marginRight: 10,
    width: 180,
  },
  imageCard: {
    width: '100%',
    height: 100,
    borderRadius: 10,
  },
  nomeProfissional: {
    fontWeight: 'bold',
    marginTop: 5,
  },
  description: {
    fontSize: 12,
    color: '#555',
  },
  circleItem: {
    alignItems: 'center',
    marginRight: 15,
  },
  circleImage: {
    width: 60,
    height: 60,
    borderRadius: 30,
    marginBottom: 5,
  },
  circleText: {
    fontSize: 12,
  },
});

export default CustomerHomeScreen;
