import React, {useEffect} from "react";
import { View, Text, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import BottomTabBar from "@/app/components/BottomBar";
import { styles } from "./styles/SearchStyle";
import { useBottomTab } from "@/app/contexts/BottomTabContext";

export default function SearchScreen(){
    const { setActiveTab } = useBottomTab();
    const WIPImage = require("../../../assets/images/estamos-em-obras.jpg");

    useEffect(()=>{
        setActiveTab('Search')
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