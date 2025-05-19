import React, {useState, useEffect, useContext} from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  FlatList,
  Image,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator
} from 'react-native';
import { getCustomerHomeInfo } from '@/app/services/auth-user.service';
import { CustomerHomeInfoResponse } from '@/app/models/User.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { useNavigation } from '@react-navigation/native';
import { Hairdresser } from '@/app/models/Hairdresser.types';
import { AuthContext } from '../../../index';

type HairdresserProfileReservationScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const CustomerHomeScreen = () => {
  const navigation = useNavigation<HairdresserProfileReservationScreenNavigationProp>();
  const { userInfo } = useContext(AuthContext);
  const [customerHomeInfo, setCustomerHomeInfo] = useState<CustomerHomeInfoResponse>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCustomerHomeInfo = async () => {
      setLoading(true);
      try {
        // Check if user is logged in
        if (!userInfo) {
          console.log("No user is logged in. Cannot fetch customer home info.");
          setLoading(false);
          return;
        }
        // Use the logged-in user's email to fetch data
        const customerHomeInfoResponse = await getCustomerHomeInfo(userInfo.customer.user.email);
        setCustomerHomeInfo(customerHomeInfoResponse);
      } catch (err) {
        console.error("Failed to get customer info:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCustomerHomeInfo();
  }, [userInfo]);

  const handleClickHairdresser = (hairdresser: Hairdresser) => {
    navigation.navigate("HairdresserProfileReservation", {hairdresser: hairdresser} )
  }

  const renderForYouItem = ({item}: any) => (
    <TouchableOpacity onPress={() => handleClickHairdresser(item)}>
        <View style={styles.card}>
        <Image
          source={{ uri: 'https://via.placeholder.com/100x100?text=Img' }}
          style={styles.imageCard}
        />
        <Text style={styles.nomeProfissional}>{item.user.first_name || 'Nome do Profissional'}{item.user.last_name || 'Nome do Profissional'}</Text>
        <Text style={styles.description}>
          {item.resume || 'Lorem Ipsum is simply dummy text of the printing and typesetting industry.'}
        </Text>
      </View>
    </TouchableOpacity>
  );

  const renderHairdresserItem = ({item} : any) => (
    <TouchableOpacity onPress={() => handleClickHairdresser(item)}>
      <View style={styles.circleItem}>
        <Image
          source={{ uri: 'https://via.placeholder.com/60x60?text=Img' }}
          style={styles.circleImage}
        />
        <Text style={styles.circleText}>{item.user.first_name || 'Title'} {item.user.last_name || 'Title'}</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#000" />
        <Text>Carregando informações...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <TextInput
        placeholder="Buscar no HairMatch"
        style={styles.searchBar}
        placeholderTextColor="#999"
      />

      {/* Seção Para Você */}
      {customerHomeInfo?.for_you && customerHomeInfo.for_you.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Para Você</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
          <FlatList
            data={customerHomeInfo.for_you}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item, index) => `para-voce-${index}`}
            renderItem={renderForYouItem}
          />
        </View>
      )}

      {/* Seção Cachos */}
      {customerHomeInfo?.hairdressers_by_preferences?.cachos && customerHomeInfo.hairdressers_by_preferences.cachos.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Cachos</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
          <FlatList
            data={customerHomeInfo.hairdressers_by_preferences.cachos}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item, index) => `cachos-${index}`}
            renderItem={renderHairdresserItem}
          />
        </View>
      )}

      {/* Seção Coloração */}
      {customerHomeInfo?.hairdressers_by_preferences?.coloracao && customerHomeInfo.hairdressers_by_preferences.coloracao.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Coloração</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
          <FlatList
            data={customerHomeInfo.hairdressers_by_preferences.coloracao}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item, index) => `coloracao-${index}`}
            renderItem={renderHairdresserItem}
          />
        </View>
      )}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
});

export default CustomerHomeScreen;
