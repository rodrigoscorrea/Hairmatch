import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  Image,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Platform,
} from 'react-native';
import { styles } from '@/styles/customer/home/styles/CustomerHomeStyle';
import { useCustomerHome } from '@/hooks/customerHooks/useCustomerHome';
import { formatText } from '@/utils/text-formater'; 
import { API_BACKEND_URL } from '@/app/_layout';

type SectionKey = 'for_you' | 'cachos' | 'coloracao' | 'barbearia' | 'trancas';

const CustomerHomeScreen = () => {
  const {
    loading,
    customerHomeInfo,
    handleClickHairdresser,
    getRandomAvatarByInferredGender,
  } = useCustomerHome();

  // Refs for each FlatList
  const flatListRefs: { [key in SectionKey]: React.RefObject<FlatList<any>> } = {
    for_you: useRef<FlatList<any>>(null),
    cachos: useRef<FlatList<any>>(null),
    coloracao: useRef<FlatList<any>>(null),
    barbearia: useRef<FlatList<any>>(null),
    trancas: useRef<FlatList<any>>(null),
  };

  // State to track the current index of each FlatList
  const [currentIndex, setCurrentIndex] = useState<{ [key in SectionKey]: number }>({
    for_you: 0,
    cachos: 0,
    coloracao: 0,
    barbearia: 0,
    trancas: 0,
  });

  // Function to handle arrow clicks
  const handleArrowClick = (section: SectionKey, direction: 'next' | 'prev') => {
    if (!customerHomeInfo) {
      return;
    }
    const ref = flatListRefs[section].current;
    if (ref) {
      const sectionData = section === 'for_you'
        ? customerHomeInfo.for_you
        : customerHomeInfo.hairdressers_by_preferences?.[section];
        
      if (!sectionData) return;

      const newIndex = currentIndex[section] + (direction === 'next' ? 1 : -1);
      if (newIndex >= 0 && newIndex < sectionData.length) {
        ref.scrollToIndex({ index: newIndex, animated: true });
        setCurrentIndex((prev) => ({ ...prev, [section]: newIndex }));
      }
    }
  };

  const renderForYouItem = ({ item }: any) => {
    const user_picture = `${API_BACKEND_URL}${item.user.profile_picture}`;
    return (
      <TouchableOpacity onPress={() => handleClickHairdresser(item)}>
        <View style={styles.card}>
          <Image
            source={
              item?.user?.profile_picture
                  ? { uri: user_picture }
                  : require('../../../assets/images/profile_picture_placeholder.png')
            }
            resizeMode='cover' 
            style={styles.imageCard} 
          />
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
    const hairdresser_picture = `${API_BACKEND_URL}${item.user.profile_picture}`;
    return (
      <TouchableOpacity onPress={() => handleClickHairdresser(item)}>
        <View style={styles.circleItem}>
          <Image
            source={
              item?.user?.profile_picture
                  ? { uri: hairdresser_picture }
                  : require('../../../assets/images/profile_picture_placeholder.png')
            }
            resizeMode='cover'
            style={styles.circleImage} 
          />
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

  // Helper to render a section
  const renderSection = (title: string, data: any[], renderItem: ({ item }: any) => JSX.Element, sectionKey: SectionKey) => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {Platform.OS === 'web' && (
          <View style={{ flexDirection: 'row' }}>
            <TouchableOpacity onPress={() => handleArrowClick(sectionKey, 'prev')}>
              <Text style={styles.arrow}>‹</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => handleArrowClick(sectionKey, 'next')}>
              <Text style={styles.arrow}>›</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
      <FlatList
        ref={flatListRefs[sectionKey]}
        data={data}
        horizontal
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item, index) => `${sectionKey}-${index}`}
        renderItem={renderItem}
      />
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>
        {customerHomeInfo ? (
          <>
            {customerHomeInfo?.for_you?.length > 0 &&
              renderSection('Para Você', customerHomeInfo.for_you, renderForYouItem, 'for_you')}

            {customerHomeInfo?.hairdressers_by_preferences?.cachos?.length > 0 &&
              renderSection(
                'Cachos',
                customerHomeInfo.hairdressers_by_preferences.cachos,
                renderHairdresserItem,
                'cachos'
              )}

            {customerHomeInfo?.hairdressers_by_preferences?.coloracao?.length > 0 &&
              renderSection(
                'Coloração',
                customerHomeInfo.hairdressers_by_preferences.coloracao,
                renderHairdresserItem,
                'coloracao'
              )}

            {customerHomeInfo?.hairdressers_by_preferences?.barbearia?.length > 0 &&
              renderSection(
                'Barbearia',
                customerHomeInfo.hairdressers_by_preferences.barbearia,
                renderHairdresserItem,
                'barbearia'
              )}

            {customerHomeInfo?.hairdressers_by_preferences?.trancas?.length > 0 &&
              renderSection(
                'Tranças',
                customerHomeInfo.hairdressers_by_preferences.trancas,
                renderHairdresserItem,
                'trancas'
              )}
          </>
        ) : (
          <>
            <View>
              <Text>
                Não foi possível recuperar cabeleireiros :C
              </Text>
            </View>
          </>
        )}
        
      </ScrollView>
    </SafeAreaView>
  );
};

export default CustomerHomeScreen;