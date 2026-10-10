import React from "react";
import { View, Text, Image, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { styles } from '../../../styles/customer/styles/ProfileStyle'; // Adjust path
import Icon from '@expo/vector-icons/Feather';
import ConfirmationModal from "@/components/modals/confirmationModal/ConfirmationModal"; // Adjust path
import MenuItem from "@/components/modals/MenuItem/MenuItem"; // Adjust path
import { ErrorModal } from "@/components/modals/ErrorModal/ErrorModal";
import { useDeleteAccount } from "@/hooks/accountHooks/useDeleteAccount";
import { useCustomerProfile } from "@/hooks/customerHooks/useCustomerProfile"; // <-- Our new hook
import { usePathname, useRouter } from 'expo-router'; // Adjust path if needed

export default function ProfileScreen(){
    const pathname = usePathname();
    const { 
      customer, 
      ratingLabel,
      isModalVisible, 
      handleLogout, 
      confirmLogout, 
      cancelLogout, 
      handleAccountSettings,
      handleAddressSettings,
      handleReceivedRatings
    } = useCustomerProfile();

    const handleMenuPress = (item: string) => {
    };

    const router = useRouter();
    const deletion = useDeleteAccount("customer");

    // userInfo is null for a moment after the logout or the account deletion.
    if (!customer) return null;

    const customer_image = customer.user.profile_picture;
    
    return (
    <SafeAreaView style={styles.safeArea}>        
        <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
          {/* Profile Header */}
          <View style={styles.profileHeader}>
              <View style={styles.profileInfo}>
                  <View style={styles.profileImageContainer}>
                      <Image 
                          source={
                            customer?.user?.profile_picture
                              ? { uri: customer_image }
                              : require('../../../assets/images/profile_picture_placeholder.png')
                          }
                          style={styles.profileImage}
                          resizeMode="cover"
                      />
                  </View>
                  <View style={styles.profileDetails}>
                      <Text style={styles.profileName}>{customer?.user?.first_name} {customer?.user?.last_name}</Text>
                      <View style={styles.profileRating}>
                          <Icon name="star" size={16} color="#eab308" />
                          <Text style={styles.ratingText}>{ratingLabel}</Text>
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
            onPress={() => handleAccountSettings()}
          />
          
          <MenuItem
            iconName="map-pin"
            title="Endereço"
            subtitle="Alterar seu endereço"
            onPress={() => handleAddressSettings()}
          />

          <MenuItem
            iconName="sliders"
            title="Preferências"
            subtitle="Alterar suas preferências"
            onPress={() => router.push('/(app)/customer/configs/preferencesSetting')}
          />
          
          <MenuItem
            iconName="star"
            title="Avaliações recebidas"
            subtitle="Veja o que os profissionais disseram sobre você"
            onPress={() => handleReceivedRatings()}
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

          <MenuItem
            iconName="trash-2"
            title="Excluir conta"
            subtitle="Apagar sua conta permanentemente"
            onPress={deletion.openDelete}
          />
        </View>

        <View style={styles.spacer} />
        </ScrollView>


      {/* Confirmation Modal */}
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