// app/(app)/(customer)/search.tsx
import React from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Image,
  Platform
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons, MaterialIcons, Entypo } from "@expo/vector-icons";
import BottomTabBar from "@/components/BottomBar";
import { styles } from "@/styles/customer/styles/SearchStyle"; // Adjust path
import { useSearch } from "@/hooks/customerHooks/useSearch"; // <-- Our new hook
import { API_BACKEND_URL } from "@/app/_layout";

export default function SearchScreen() {
  const {
    searchText,
    setSearchText,
    loading,
    hairdresserResults,
    serviceResults,
    handleNavigateToHairdresser,
    handleNavigateToService,
    handleGoBack
  } = useSearch();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
      <View style={styles.Headercontainer}>
        {Platform.OS === 'web' && (
          <TouchableOpacity onPress={handleGoBack} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#333" />
          </TouchableOpacity>
        )}
        <View style={styles.searchWrapper}>
          <Ionicons name="search" size={20} color="#7B3F00" style={styles.iconLeft} />
          <TextInput
            style={styles.input}
            placeholder="Busque por profissionais, serviços..."
            value={searchText}
            onChangeText={setSearchText}
            placeholderTextColor="#7B3F00"
          />
          <MaterialIcons name="filter-list" size={24} color="#7B3F00" style={styles.iconRight} />
        </View>
      </View>
        
        {loading ? (
          <ActivityIndicator size="large" color="#FF6B00" style={{ marginTop: 20 }} />
        ) : (
          <>
            {/* Render Hairdresser Results */}
            {hairdresserResults.length > 0 && hairdresserResults.map((result) => (
              <TouchableOpacity style={styles.card} key={`hairdresser-${result.id}`} onPress={() => handleNavigateToHairdresser(result.id!)}>
                <Image source={{uri: `${result.user.profile_picture}`}} style={styles.avatar} />
                <View style={styles.info}>
                  <Text style={styles.name}>{`${result.user.first_name} ${result.user.last_name}`}</Text>
                  <View style={styles.ratingRow}>
                    <Ionicons name="star" size={16} color="#FFB800" />
                    <Text style={styles.ratingText}>{result.user.rating?.toFixed(1) || "5.0"}</Text>
                  </View>
                  <View style={styles.locationRow}>
                    <Entypo name="location-pin" size={16} color="#7B3F00" />
                    <Text style={styles.address} numberOfLines={1}>
                      {result.user.neighborhood}, {result.user.city}
                    </Text>
                  </View>
                </View>
                <View style={styles.goButton}>
                  <Ionicons name="arrow-forward" size={20} color="#7B3F00" />
                </View>
              </TouchableOpacity>
            ))}

            {/* Render Service Results */}
            {serviceResults.length > 0 && serviceResults.map((result) => (
              <TouchableOpacity style={styles.card} key={`service-${result.id}`} onPress={() => handleNavigateToService(result)}>
                <View style={styles.avatar} />
                <View style={styles.info}>
                  <Text style={styles.name}>{result.name}</Text>
                  <Text style={styles.info}>R$ {result.price}</Text>
                   <Text style={styles.info} numberOfLines={1}>
                      por {result.hairdresser!.user!.first_name} {result.hairdresser.user.last_name}
                    </Text>
                </View>
                <View style={styles.goButton}>
                  <Ionicons name="arrow-forward" size={20} color="#7B3F00" />
                </View>
              </TouchableOpacity>
            ))}

            {/* No Results Message */}
            {!loading && searchText.length > 0 && hairdresserResults.length === 0 && serviceResults.length === 0 && (
                <View>
                    <Text style={styles.info}>Nenhum resultado foi encontrado para "{searchText}"</Text>
                </View>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}