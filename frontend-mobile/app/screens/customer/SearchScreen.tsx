import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons, MaterialIcons, Entypo } from "@expo/vector-icons";
import BottomTabBar from "@/app/components/BottomBar";
import { useBottomTab } from "@/app/contexts/BottomTabContext";
import { styles } from "./styles/SearchStyle";
import { searchHairdressers } from "@/app/services/auth-user.service";
import { Hairdresser } from "@/app/models/Hairdresser.types";
import { RootStackParamList } from '@/app/models/RootStackParams.types';
import { StackNavigationProp } from '@react-navigation/stack';
import { useNavigation } from '@react-navigation/native';
import { ServiceRequest } from "@/app/models/Service.types";

type CustomerSearchScreenNavigationProp = StackNavigationProp<RootStackParamList>;
export default function SearchScreen() {
  const { setActiveTab, customer } = useBottomTab();
  const [searchText, setSearchText] = useState("");
  const [hairdresserResults, setHairdresserResults] = useState<Hairdresser[]>([]);
  const [serviceResults, setServiceResults] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);
  const navigation = useNavigation<CustomerSearchScreenNavigationProp>();
  const fetchResults = async (query: string) => {
    try {
      setLoading(true);
      const data = await searchHairdressers(query);
      data.map((item: any) => {
        if(item.result_type === 'hairdresser') setHairdresserResults([...hairdresserResults, item])
        else if (item.result === 'service') setServiceResults([...serviceResults, item])
        return;
      });
    } catch (error) {
      console.error("Error searching for hairdressers:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setActiveTab("Search");
  }, []);

  useEffect(() => {
    if (debounceTimeout) clearTimeout(debounceTimeout);

    const timeout = setTimeout(() => {
      if (searchText.trim().length > 0) {
        fetchResults(searchText);
      } else {
        setHairdresserResults([]);
        setServiceResults([]);
      }
    }, 1500);

    setDebounceTimeout(timeout);
    return () => clearTimeout(timeout);
  }, [searchText]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.searchWrapper}>
        <Ionicons name="search" size={20} color="#7B3F00" style={styles.iconLeft} />
        <TextInput
          style={styles.input}
          placeholder="Busque por profissionais, serviços, preferências, técnicas..."
          value={searchText}
          onChangeText={setSearchText}
          placeholderTextColor="#7B3F00"
        />
        <MaterialIcons name="filter-list" size={24} color="#7B3F00" style={styles.iconRight} />
      </View>
      

      {loading ? 
      (
        <>
            <ActivityIndicator></ActivityIndicator>
        </>
      ) : 
      (
        <>
            {hairdresserResults ? (
                hairdresserResults.map((result) => (
                    <TouchableOpacity style={styles.card} key={result.id} onPress={()=> navigation.navigate('HairdresserProfileReservation', {hairdresser: result, avatar: ''})}>
                        <View style={styles.avatar} />
                        <View style={styles.info}>
                            <Text style={styles.name}>{`${result.user.first_name} ${result.user.last_name}`}</Text>
                            <View style={styles.ratingRow}>
                                <Ionicons name="star" size={16} color="#FFB800" />
                                <Text style={styles.ratingText}>{result.user.rating?.toFixed(1) || "5.0"}</Text>
                            </View>
                        <View style={styles.locationRow}>
                        <Entypo name="location-pin" size={16} color="#7B3F00" />
                        <Text style={styles.address} numberOfLines={2}>
                            {result.user.address}, {result.user.number}{"\n"}
                            {result.user.neighborhood}, {result.user.city} - {result.user.state}, {result.user.postal_code}
                        </Text>
                        </View>
                    </View>

                    <View style={styles.goButton} >
                        <Ionicons name="arrow-forward" size={20} color="#7B3F00" />
                    </View>
                    </TouchableOpacity>
                ))
            ):(
                <View>
                    <Text>Nenhum resultado foi encotrado.</Text>
                </View>
            )}
            {serviceResults ? (
                serviceResults.map((result) => (
                    <TouchableOpacity style={styles.card} key={result.id} onPress={()=> {
                        navigation.navigate('ServiceBooking', {
                            hairdresser: result.hairdresser, 
                            customer_id: customer!.id,
                            service: result,
                            })}}>
                        <View style={styles.avatar} />
                        <View style={styles.info}>
                            <Text style={styles.name}>{`${result.name}`}</Text>
                        <View style={styles.locationRow}>
                        <Entypo name="location-pin" size={16} color="#7B3F00" />
                        <Text style={styles.address} numberOfLines={2}>
                            Valor: R$ {result.price}{"\n"}
                            Duração:  {result.duration}
                        </Text>
                        </View>
                    </View>

                    <View style={styles.goButton} >
                        <Ionicons name="arrow-forward" size={20} color="#7B3F00" />
                    </View>
                    </TouchableOpacity>
                ))
            ):(
                <View>
                    <Text>Nenhum resultado foi encotrado.</Text>
                </View>
            )}
        </>
      )}
        

      <BottomTabBar />
    </SafeAreaView>
  );
}
