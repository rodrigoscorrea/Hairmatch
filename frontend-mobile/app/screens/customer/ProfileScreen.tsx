import React, { useEffect, useContext } from "react";
import { View, Text, Image, TouchableOpacity, ScrollView} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from '@/app/components/BottomBar';
import { useBottomTab } from "@/app/contexts/BottomTabContext";
import { styles } from "./styles/ProfileStyle";
import Icon from 'react-native-vector-icons/Feather';

interface MenuItemProps {
    iconName: string;
    title: string;
    subtitle: string;
    onPress?: () => void;
}
  
const MenuItem: React.FC<MenuItemProps> = ({ iconName, title, subtitle, onPress }) => (
    <TouchableOpacity style={styles.menuItem} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.menuItemLeft}>
        <Icon name={iconName} size={20} color="#000000" />
        <View style={styles.menuTextContainer}>
          <Text style={styles.menuTitle}>{title}</Text>
          <Text style={styles.menuSubtitle}>{subtitle}</Text>
        </View>
      </View>
      <View style={styles.menuArrow}>
        <Icon name="chevron-right" size={16} color="#ffffff" />
      </View>
    </TouchableOpacity>
);

export default function ProfileScreen(){
    const { setActiveTab } = useBottomTab();

    useEffect(()=>{
        setActiveTab('Profile')
    }, [])

    const handleMenuPress = (item: string) => {
        console.log(`Pressed ${item}`);
    };
    
    const handleNavPress = (tab: string) => {
    console.log(`Navigated to ${tab}`);
    };

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
                <Text style={styles.profileName}>Fulana</Text>
                <View style={styles.profileRating}>
                <Icon name="star" size={16} color="#eab308" />
                <Text style={styles.ratingText}>5.0</Text>
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
            onPress={() => handleMenuPress('Sair')}
          />
        </View>

        <View style={styles.spacer} />
        </ScrollView>

        {/* Bottom Navigation */}
        <BottomTabBar />
        
    </SafeAreaView>
    );
}