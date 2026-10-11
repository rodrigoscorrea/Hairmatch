import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import {styles} from '../../../styles/customer/styles/ProfileStyle';
import Icon from '@expo/vector-icons/Feather';

interface MenuItemProps {
    iconName: React.ComponentProps<typeof Icon>["name"];
    title: string;
    subtitle: string;
    onPress?: () => void;
    // A short text shown before the arrow, like the number of unread notifications.
    badge?: string;
}

const badgeStyles = StyleSheet.create({
    right: { flexDirection: "row", alignItems: "center" },
    badge: {
      minWidth: 22,
      height: 22,
      borderRadius: 11,
      paddingHorizontal: 6,
      marginRight: 8,
      backgroundColor: "#FC7C25",
      alignItems: "center",
      justifyContent: "center",
    },
    badgeText: { color: "#ffffff", fontSize: 12, fontWeight: "bold" },
});
  
const MenuItem: React.FC<MenuItemProps> = ({ iconName, title, subtitle, onPress, badge }) => (
    <TouchableOpacity style={styles.menuItem} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.menuItemLeft}>
        <Icon name={iconName} size={20} color="#000000" />
        <View style={styles.menuTextContainer}>
          <Text style={styles.menuTitle}>{title}</Text>
          <Text style={styles.menuSubtitle}>{subtitle}</Text>
        </View>
      </View>
      <View style={badgeStyles.right}>
        {badge ? (
          <View style={badgeStyles.badge} accessibilityLabel={`${badge} não lidas`}>
            <Text style={badgeStyles.badgeText}>{badge}</Text>
          </View>
        ) : null}
        <View style={styles.menuArrow}>
          <Icon name="chevron-right" size={16} color="#ffffff" />
        </View>
      </View>
    </TouchableOpacity>
);

export default MenuItem;