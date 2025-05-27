import React, { useEffect, useContext } from "react";
import { View, Text, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from "@/app/components/BottomBar";
import { useBottomTab } from "@/app/contexts/BottomTabContext";
import { styles } from "./styles/ProfileStyle";

export default function ProfileScreen(){
    const { customer, setActiveTab } = useBottomTab();

    const WIPImage = require("../../../assets/images/estamos-em-obras.jpg");

    useEffect(()=>{
        setActiveTab('CustomerProfile')
    }, [])

    return (
        <SafeAreaView style={styles.container}>
            <View style={{flex: 1}}>
                <Text>Tela ainda não desenvolvida</Text>
                <Image source={WIPImage} style={styles.wipImage}></Image>
            </View>
             <BottomTabBar />
        </SafeAreaView>
    )
}