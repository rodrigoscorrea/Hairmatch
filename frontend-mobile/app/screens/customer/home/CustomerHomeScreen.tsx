import React, {useState, useEffect, useContext, useMemo} from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  Image,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView
} from 'react-native';
import { styles } from './styles/CustomerHomeStyle';
import { getCustomerHomeInfo } from '@/app/services/auth-user.service';
import { CustomerHomeInfoResponse } from '@/app/models/User.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { useNavigation } from '@react-navigation/native';
import { Hairdresser } from '@/app/models/Hairdresser.types';
import { AuthContext } from '../../../index';
import { formatText } from '@/app/utils/text-formater';
import BottomTabBar from '@/app/components/BottomBar';
import { useBottomTab } from '@/app/contexts/BottomTabContext';

type HairdresserProfileReservationScreenNavigationProp = StackNavigationProp<RootStackParamList>;

const CustomerHomeScreen = () => {
  const navigation = useNavigation<HairdresserProfileReservationScreenNavigationProp>();
  const { userInfo } = useContext(AuthContext);
  const [customerHomeInfo, setCustomerHomeInfo] = useState<CustomerHomeInfoResponse>();
  const [loading, setLoading] = useState(true);
  const { setActiveTab } = useBottomTab();

  //apenas para demonstração do MVP
  const maleNames = ["Luis Felipe", "Murilo", "Nicolas", "João Vitor", "Thomas", "Gustavo Henrique", "Thiago", "Igor", "Otávio", "Vitor Gabriel", "Bruno", "João Guilherme", "Cauã", "Guilherme", "Leonardo", "Breno", "Lucca"];
  const femaleNames = ["Luna", "Luiza", "Sarah", "Nicole", "Bárbara", "Beatriz", "Larissa", "Isabella", "Helena", "Luisa", "Maria Flor", "Ana Sophia", "Heloisa", "Isabel", "Isabel", "Daniela", "Ana Clara", "Maria Cecília", "Maria Julia", "Yasmin", "Lara", "Luana"];

  const maleAvatar = [
    require("../../../../assets/hairdressers/male/male1.jpg"),
    require("../../../../assets/hairdressers/male/male2.jpg"),
    require("../../../../assets/hairdressers/male/male3.jpg"),
    require("../../../../assets/hairdressers/male/male4.jpg"),
    require("../../../../assets/hairdressers/male/male5.jpg")
  ];

  const femaleAvatar = [
    require("../../../../assets/hairdressers/female/female1.jpg"),
    require("../../../../assets/hairdressers/female/female2.jpg"),
    require("../../../../assets/hairdressers/female/female3.jpg"),
    require("../../../../assets/hairdressers/female/female4.jpg"),
    require("../../../../assets/hairdressers/female/female5.jpg")
  ];

  const defaultAvatar  = require("../../../../assets/hairdressers/male/default.jpg");

  const inferGenderFromName = (firstName: string): 'male' | 'female' | 'unknown' => {
    if (maleNames.includes(firstName)) {
      return 'male';
    }
    if (femaleNames.includes(firstName)) {
      return 'female';
    }
    return 'unknown'; // Caso o nome não esteja em nenhuma lista
  };

  const getRandomAvatarByInferredGender = (firstName: string) => {
    const gender = inferGenderFromName(firstName);
  
    let selectedAvatars;
    if (gender === 'male') {
      selectedAvatars = maleAvatar;
    } else if (gender === 'female') {
      selectedAvatars = femaleAvatar;
    } else {
      return defaultAvatar;
    }
  
    if (selectedAvatars.length === 0) {
        return defaultAvatar; 
    }
  
    const randomIndex = Math.floor(Math.random() * selectedAvatars.length);
    return selectedAvatars[randomIndex];
  };
  //aqui acaba as funções somente de demonstração pro MVP

  useEffect(() => {
    const fetchCustomerHomeInfo = async () => {
      setLoading(true);
      try {
        const customerHomeInfoResponse = await getCustomerHomeInfo(
          userInfo ?
          userInfo.customer.user.email :
          ''
        );
        setCustomerHomeInfo(customerHomeInfoResponse);
      } catch (err) {
        console.error("Failed to get customer info:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCustomerHomeInfo();
    setActiveTab('CustomerHome');
  }, [userInfo]);

  const handleClickHairdresser = (hairdresser: Hairdresser, avatar: any) => {
    navigation.navigate("HairdresserProfileReservation", {hairdresser: hairdresser, avatar:avatar} ) //ajustar o RootStackParamList 
  }

  const renderForYouItem = ({item}: any) => {
    //somente para demonstração do MVP
    const avatarSource = getRandomAvatarByInferredGender(item.user.first_name);
    return(
      <TouchableOpacity onPress={() => handleClickHairdresser(item, avatarSource)}>
        <View style={styles.card}>
        <Image
          source={avatarSource}
          style={styles.imageCard}
        />
        <View style={{display:'flex', flexDirection: 'row', marginBottom: 3}}>
          <Text style={styles.nomeProfissional}>{item.user.first_name || 'Nome do Profissional'}</Text>
          <Text style={styles.sobrenomeProfissional}>{item.user.last_name || 'Nome do Profissional'}</Text>
        </View>
        <Text style={styles.description}>
          {formatText(item.resume) || 'Lorem Ipsum is simply dummy text of the printing and typesetting industry.'}
        </Text>
      </View>
    </TouchableOpacity>
    )
  };

  const renderHairdresserItem = ({item} : any) => { //mudei de ( para {
    //somente para teste
    const avatarSource = getRandomAvatarByInferredGender(item.user.first_name);
    return(
      <TouchableOpacity onPress={() => handleClickHairdresser(item, avatarSource)}>
      <View style={styles.circleItem}>
        <Image
          source={avatarSource}
          style={styles.circleImage}
        />
        <Text style={styles.circleText}>{item.user.first_name || 'Title'}</Text>
        <Text style={styles.circleText}>{item.user.last_name || 'Title'}</Text>
      </View>
    </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#000" />
          <Text>Carregando informações...</Text>
        </View>
        <BottomTabBar />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>

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

      {/* Seção Barbearia */}
      {customerHomeInfo?.hairdressers_by_preferences?.barbearia && customerHomeInfo.hairdressers_by_preferences.barbearia.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Barbearia</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
          <FlatList
            data={customerHomeInfo.hairdressers_by_preferences.barbearia}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item, index) => `barbearia-${index}`}
            renderItem={renderHairdresserItem}
          />
        </View>
      )}

      {/* Seção Tranças */}
      {customerHomeInfo?.hairdressers_by_preferences?.trancas && customerHomeInfo.hairdressers_by_preferences.trancas.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Tranças</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
          <FlatList
            data={customerHomeInfo.hairdressers_by_preferences.trancas}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item, index) => `trancas-${index}`}
            renderItem={renderHairdresserItem}
          />
        </View>
      )}
      </ScrollView>
      <BottomTabBar/>
    </SafeAreaView>
  );
};

export default CustomerHomeScreen;
