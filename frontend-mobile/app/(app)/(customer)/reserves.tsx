// app/(app)/(customer)/reserves.tsx

import { ActivityIndicator, Text, View, SafeAreaView, TouchableOpacity, ScrollView, Image } from 'react-native'
import { styles } from '@/styles/customer/styles/ReserveStyle'; // Adjust path
import React from 'react'
import BottomTabBar from '@/components/BottomBar'; // Adjust path
import { formatDate } from '@/utils/date-formater'; // Adjust path
import { formatTime } from '@/utils/time-formater'; // Adjust path
import { useReserves } from '@/hooks/customerHooks/useReserves'; // <-- Our new hook
import { API_BACKEND_URL } from '@/app/_layout';

export default function ReservesScreen() {
  const { isLoading, reserves, getStatusColor, handleNavigateToDetails } = useReserves();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <View style={styles.content}>
          <Text style={styles.headerText}>Meus Agendamentos</Text>
          
          {isLoading ? ( 
            <ActivityIndicator size="large" color="#FF6B00" style={styles.loader} />
          ) : reserves.length > 0 ? (
            <View style={styles.reservesContainer}>
              {reserves.map((reserve) => (
                <View key={reserve.id} style={styles.reserveCard}>
                  <View style={styles.hairdresserInfoContainer}>
                    <Image source={{uri: `${reserve.service.hairdresser.user.profile_picture}`}} style={styles.profileCircle} />
                    <View style={styles.hairdresserDetailsContainer}>
                      <View style={{display: 'flex', flexDirection: 'row'}}>
                        <Text style={styles.hairdresserFirstName}>
                          {reserve.service.hairdresser.user.first_name}
                        </Text>
                        <Text style={styles.hairdresserLastName}>
                          {reserve.service.hairdresser.user.last_name}
                        </Text>
                      </View>
                      <Text style={styles.reserveDetailText}>
                        {`Dia: ${formatDate(reserve.start_time)}`}
                        <Text style={styles.spacer}> · </Text>
                        {`Hora: ${formatTime(reserve.start_time)}`}
                      </Text>
                      <Text style={styles.reserveDetailText}>
                        {`Serviço: ${reserve.service.name}`}
                      </Text>
                      <View style={styles.statusContainer}>
                        <Text style={styles.statusLabel}>Status:</Text>
                        <Text style={[styles.statusValue, { color: getStatusColor('aguardando confirmação') }]}>
                          { 'Aguardando confirmação' }
                        </Text>
                      </View>
                    </View>
                  </View>
                  
                  <TouchableOpacity style={styles.moreInfoButton} onPress={() => handleNavigateToDetails(reserve.id)}>
                    <Text style={styles.moreInfoButtonText}>Mais Informações</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>Você ainda não possui agendamentos</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}