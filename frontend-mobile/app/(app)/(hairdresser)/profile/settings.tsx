import React from "react";
import { View, Text, Image, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { styles } from '@/styles/hairdresser/profile/styles/HairdresserSettingsStyle'; // Adjust path
import Icon from 'react-native-vector-icons/Feather';
import ConfirmationModal from "@/components/modals/confirmationModal/ConfirmationModal"; // Adjust path
import MenuItem from "@/components/modals/MenuItem/MenuItem"; // Adjust path
import { useHairdresserSettings } from "@/hooks/hairdresserHooks/useHairdresserSettings"; // <-- Our new hook
import { Ionicons } from "@expo/vector-icons";
import { API_BACKEND_URL } from "@/app/_layout";

export default function HairdresserSettingsScreen(){
    const { hairdresser, isModalVisible, handleLogout, confirmLogout, cancelLogout, handleBack } = useHairdresserSettings();
    const fallbackImage = 'https://images.unsplash.com/photo-1494790108755-2616c28c5ad2?w=64&h=64&fit=crop&crop=face';
      const profilePictureUrl = hairdresser?.user?.profile_picture
          ? `${API_BACKEND_URL}${hairdresser.user.profile_picture}`
          : fallbackImage;
    return (
    <SafeAreaView style={styles.safeArea}>        
        <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
            <View style={styles.profileInfo}>
            <View style={styles.profileImageContainer}>
                <Image 
                    source={{ uri: profilePictureUrl }}
                    style={styles.profileImage}
                    resizeMode="cover"
                />
            </View>
            <View style={styles.profileDetails}>
                <Text style={styles.profileName}>{hairdresser?.user.first_name} {hairdresser?.user.last_name}</Text>
                <View style={styles.profileRating}>
                <Icon name="star" size={16} color="#eab308" />
                <Text style={styles.ratingText}>{hairdresser?.user.rating}</Text>
                </View>
            </View>
            </View>
        </View>

        {/* Menu Items */}
        <View style={styles.menuContainer}>
            <MenuItem
            iconName="user"
            title="Dados da Conta"
            subtitle="Editar informações da sua conta"
          />
          
          <MenuItem
            iconName="map-pin"
            title="Endereço"
            subtitle="Alterar seu endereço"
          />
          
          <MenuItem
            iconName="heart"
            title="Favoritos"
            subtitle="Veja seus profissionais favoritos"
          />
          
          <MenuItem
            iconName="bell"
            title="Notificações"
            subtitle="Gerenciar suas notificações"
          />
          
          <MenuItem
            iconName="help-circle"
            title="Ajuda"
            subtitle="Entre em contato com o suporte"
          />
          
          <MenuItem
            iconName="log-out"
            title="Sair"
            subtitle="Fazer logout da conta"
            onPress={handleLogout}
          />
        </View>

        <View style={styles.spacer} />
        </ScrollView>

        {/* Logout Confirmation Modal */}
        <ConfirmationModal
            visible={isModalVisible}
            title="Deseja realmente sair do Hairmatch?"
            description="Você terá de entrar novamente para continuar utilizando o sistema"
            confirmText="Sim, tenho certeza"
            onConfirm={confirmLogout}
            onCancel={cancelLogout}
        />
    </SafeAreaView>
    );
}