import React from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from "@/app/components/BottomBar";

export default function ReservesScreen(){
    return (
        <SafeAreaView>
            <View>
                <Text>RESERVE SCREEN</Text>
            </View>
            <BottomTabBar activeTab="Reserves" />
        </SafeAreaView>
    )
}