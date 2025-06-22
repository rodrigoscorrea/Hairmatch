import React from "react";
import { View, Text, TouchableOpacity} from "react-native";
import {styles} from '../../../styles/customer/styles/ProfileStyle';
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

export default MenuItem;