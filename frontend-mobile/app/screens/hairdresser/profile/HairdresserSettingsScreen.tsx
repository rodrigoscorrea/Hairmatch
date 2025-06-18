import React, { useEffect, useContext, useState } from "react";
import { View, Text, Image, TouchableOpacity, ScrollView, Alert} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from '@/app/components/BottomBar';
import { useBottomTab } from "@/app/contexts/BottomTabContext";
import { styles } from './styles/HairdresserSettingsStyle';
import Icon from 'react-native-vector-icons/Feather';
import { AuthContext } from '../../../index';
import ConfirmationModal from "@/app/components/modals/confirmationModal/ConfirmationModal";
import { AuthContextType } from "@/app/models/Auth.types";
import MenuItem from "@/app/components/modals/MenuItem/MenuItem";

export default function HairdresserSettingsScreen(){
    const { setActiveTab, hairdresser } = useBottomTab();
    const { signOut } = useContext<AuthContextType>(AuthContext);
    const [isModalVisible, setIsModalVisible] = useState<boolean>(false);
    useEffect(()=>{
        setActiveTab('Profile')
    }, [])

    const handleMenuPress = (item: string) => {
        console.log(`Pressed ${item}`);
    };
    
    const handleNavPress = (tab: string) => {
      console.log(`Navigated to ${tab}`);
    };

    const handleLogout = () => {
      setIsModalVisible(true);
    }

    return (
    <SafeAreaView style={styles.safeArea}>        
        <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
            <View style={styles.profileInfo}>
            <View style={styles.profileImageContainer}>
                <Image 
                source={{ uri: 'https://images.unsplash.com/photo-1494790108755-2616c28c5ad2?w=64&h=64&fit=crop&crop=face' }}
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
            onPress={() => handleMenuPress('Dados da Conta')}
          />
          
          <MenuItem
            iconName="map-pin"
            title="Endereço"
            subtitle="Alterar seu endereço"
            onPress={() => handleMenuPress('Endereço')}
          />
          
          <MenuItem
            iconName="heart"
            title="Favoritos"
            subtitle="Veja seus profissionais favoritos"
            onPress={() => handleMenuPress('Favoritos')}
          />
          
          <MenuItem
            iconName="bell"
            title="Notificações"
            subtitle="Gerenciar suas notificações"
            onPress={() => handleMenuPress('Notificações')}
          />
          
          <MenuItem
            iconName="help-circle"
            title="Ajuda"
            subtitle="Entre em contato com o suporte"
            onPress={() => handleMenuPress('Ajuda')}
          />
          
          <MenuItem
            iconName="log-out"
            title="Sair"
            subtitle="Fazer logout da conta"
            onPress={() => handleLogout()}
          />
        </View>

        <View style={styles.spacer} />
        </ScrollView>

        {/* Bottom Navigation */}
        <BottomTabBar />

      {isModalVisible && (
        <ConfirmationModal
            visible={isModalVisible}
            title="Deseja realmente sair do Hairmatch?"
            description="Você terá de entrar novamente para continuar utilizando o sistema"
            confirmText="Sim, tenho certeza"
            onConfirm={async () => {
                await signOut();
                setIsModalVisible(false);
            }}
            onCancel={() => {
                setIsModalVisible(false);
            }}
        />
        )}  
    </SafeAreaView>
    );
}