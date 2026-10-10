import React from "react";
import { View, Text, Image, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { styles } from '@/styles/hairdresser/profile/styles/HairdresserSettingsStyle'; // Adjust path
import Icon from '@expo/vector-icons/Feather';
import ConfirmationModal from "@/components/modals/confirmationModal/ConfirmationModal"; // Adjust path
import MenuItem from "@/components/modals/MenuItem/MenuItem"; // Adjust path
import { ErrorModal } from "@/components/modals/ErrorModal/ErrorModal";
import { useDeleteAccount } from "@/hooks/accountHooks/useDeleteAccount";
import { useHairdresserSettings } from "@/hooks/hairdresserHooks/useHairdresserSettings"; // <-- Our new hook
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

export default function HairdresserSettingsScreen(){
    const { hairdresser, isModalVisible, handleLogout, confirmLogout, cancelLogout, handleBack, handleAccountSettings, handleAddressSettings } = useHairdresserSettings();
    const router = useRouter();
    const deletion = useDeleteAccount("hairdresser");
    // userInfo is null for a moment after the logout or the account deletion.
    if (!hairdresser) return null;
    const hairdresser_image = hairdresser.user.profile_picture;
    return (
    <SafeAreaView style={styles.safeArea}>        
        <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
            <View style={styles.profileInfo}>
            <View style={styles.profileImageContainer}>
                <Image 
                    source={
                      hairdresser?.user?.profile_picture
                          ? { uri: hairdresser_image }
                          : require('../../../../assets/images/profile_picture_placeholder.png')
                    }
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
            onPress={handleAccountSettings}
          />
          
          <MenuItem
            iconName="map-pin"
            title="Endereço"
            subtitle="Alterar seu endereço"
            onPress={handleAddressSettings}
          />

          <MenuItem
            iconName="sliders"
            title="Preferências"
            subtitle="Alterar suas preferências"
            onPress={() => router.push('/(app)/hairdresser/configs/preferencesSetting')}
          />

          <MenuItem
            iconName="file-text"
            title="Resumo"
            subtitle="Editar a descrição do seu perfil"
            onPress={() => router.push('/(app)/hairdresser/configs/resumeSetting')}
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

          <MenuItem
            iconName="trash-2"
            title="Excluir conta"
            subtitle="Apagar sua conta permanentemente"
            onPress={deletion.openDelete}
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

        {/* Account deletion */}
        <ConfirmationModal
            visible={deletion.confirmVisible}
            title="Deseja realmente excluir sua conta?"
            description={deletion.description}
            confirmText={deletion.deleting ? "Excluindo..." : "Sim, excluir"}
            onConfirm={deletion.confirmDelete}
            onCancel={deletion.cancelDelete}
        />
        <ErrorModal
            visible={deletion.errorModal.visible}
            onClose={deletion.closeError}
            message={deletion.errorModal.message}
        />
    </SafeAreaView>
    );
}