import React from 'react';
import {
  View,
  Text,
  FlatList,
  Image,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView
} from 'react-native';
import { styles } from '@/screens/customer/home/styles/CustomerHomeStyle'; // Adjust path if needed
import { useCustomerHome } from '@/hooks/customerHooks/useCustomerHome'; // <-- Import our new hook
import BottomTabBar from '@/components/BottomBar'; // Adjust path
import { formatText } from '@/utils/text-formater'; // Adjust path

// This component is now much cleaner!
const CustomerHomeScreen = () => {
  const {
    loading,
    customerHomeInfo,
    handleClickHairdresser,
    getRandomAvatarByInferredGender
  } = useCustomerHome();

  const renderForYouItem = ({ item }: any) => {
    const avatarSource = getRandomAvatarByInferredGender(item.user.first_name);
    return (
      <TouchableOpacity onPress={() => handleClickHairdresser(item, avatarSource)}>
        <View style={styles.card}>
          <Image source={avatarSource} style={styles.imageCard} />
          <View style={{ display: 'flex', flexDirection: 'row', marginBottom: 3 }}>
            <Text style={styles.nomeProfissional}>{item.user.first_name || 'Nome'}</Text>
            <Text style={styles.sobrenomeProfissional}>{item.user.last_name || ''}</Text>
          </View>
          <Text style={styles.description}>
            {formatText(item.resume) || 'Lorem Ipsum...'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  const renderHairdresserItem = ({ item }: any) => {
    const avatarSource = getRandomAvatarByInferredGender(item.user.first_name);
    return (
      <TouchableOpacity onPress={() => handleClickHairdresser(item, avatarSource)}>
        <View style={styles.circleItem}>
          <Image source={avatarSource} style={styles.circleImage} />
          <Text style={styles.circleText}>{item.user.first_name || 'Title'}</Text>
          <Text style={styles.circleText}>{item.user.last_name || ''}</Text>
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
    </SafeAreaView>
  );
};

export default CustomerHomeScreen;
