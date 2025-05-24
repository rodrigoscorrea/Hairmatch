import React, { useEffect, useContext } from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from "@/app/components/BottomBar";
import { useBottomTab } from "@/app/contexts/BottomTabContext";

export default function ProfileScreen(){
    const { customer, setActiveTab } = useBottomTab();

    useEffect(()=>{
        setActiveTab('CustomerProfile');   
    })

    return (
        <SafeAreaView>
            <View>
                <Text>CUSTOMER PROFILE SCREEN</Text>
            </View>
            <BottomTabBar/>
        </SafeAreaView>
    )
}