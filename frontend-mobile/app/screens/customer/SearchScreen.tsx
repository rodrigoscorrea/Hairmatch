import React from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from "@/app/components/BottomBar";

export default function SearchScreen(){
    return (
        <SafeAreaView>
            <View>
                <Text>SEARCH SCREEN</Text>
            </View>
             <BottomTabBar activeTab="Search" />
        </SafeAreaView>
    )
}