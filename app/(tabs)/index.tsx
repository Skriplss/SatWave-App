import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { router } from "expo-router";
import { Camera, MapPin, Send, Bot, Leaf } from "lucide-react-native";
import { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform,
  Animated,
  Dimensions,
  ActivityIndicator,
  ScrollView,
  TextInput,
  KeyboardAvoidingView,
  Image,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
// Local fallback for AI analysis to avoid external SDK
import { generateObject } from "@/lib/ai";
import { z } from "zod";
import Colors from "@/constants/colors";
import { TrashType, TRASH_TYPES } from "@/constants/trash-types";
import { useApp } from "@/contexts/app-context";
import { ScanResult } from "@/types/app";
import { postPhoto } from "@/lib/api";

const { width } = Dimensions.get("window");

const AnalysisSchema = z.object({
  trashType: z.enum([
    "plastic",
    "paper",
    "glass",
    "metal",
    "organic",
    "electronic",
    "textile",
    "battery",
    "general",
  ]),
  confidence: z.number().min(0).max(100),
  description: z.string(),
});

type Message = {
  id: string;
  type: "bot" | "user";
  text?: string;
  imageUri?: string;
  location?: { latitude: number; longitude: number; address?: string };
  timestamp: number;
};

type ChatState = "idle" | "awaiting_image" | "analyzing" | "awaiting_location" | "processing";

type PendingAnalysis = {
  imageUri: string;
  analysis: z.infer<typeof AnalysisSchema>;
};

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const { addScan } = useApp();
  const [messages, setMessages] = useState<Message[]>([{
    id: "welcome",
    type: "bot",
    text: "👋 Hello! I'm your EcoRecycle assistant. Upload a photo of trash to get started and earn points for helping the planet!",
    timestamp: Date.now(),
  }]);
  const [chatState, setChatState] = useState<ChatState>("idle");
  const [pendingAnalysis, setPendingAnalysis] = useState<PendingAnalysis | null>(null);
  const [inputText, setInputText] = useState("");
  const scrollViewRef = useRef<ScrollView>(null);
  const [locationPermission, requestLocationPermission] = Location.useForegroundPermissions();

  useEffect(() => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [messages]);

  const addBotMessage = (text: string) => {
    const msg: Message = {
      id: `bot_${Date.now()}_${Math.random()}`,
      type: "bot",
      text,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, msg]);
  };

  const addUserMessage = (content: Partial<Message>) => {
    const msg: Message = {
      id: `user_${Date.now()}_${Math.random()}`,
      type: "user",
      timestamp: Date.now(),
      ...content,
    };
    setMessages(prev => [...prev, msg]);
  };

  const analyzeImage = async (imageUri: string) => {
    try {
      setChatState("analyzing");
      addBotMessage("🔍 Analyzing your image...");

      console.log("Starting image analysis...");
      
      let result;
      try {
        result = await generateObject({
          messages: [
            {
              role: "user",
              content: [
                {
                  type: "image",
                  image: imageUri,
                },
                {
                  type: "text",
                  text: "Analyze this image and identify the type of trash/waste visible. Return the trash type, confidence level (0-100), and a brief description of what you see.",
                },
              ],
            },
          ],
          schema: AnalysisSchema,
        });
      } catch (apiError) {
        console.error("API Error:", apiError);
        if (apiError instanceof Error) {
          console.error("Error message:", apiError.message);
          console.error("Error stack:", apiError.stack);
        }
        throw new Error("Failed to connect to AI service. Please check your internet connection and try again.");
      }

      console.log("Analysis result:", JSON.stringify(result, null, 2));

      if (!result || typeof result !== 'object') {
        throw new Error("Invalid response format from AI");
      }

      if (!result.trashType) {
        throw new Error("AI could not identify trash type");
      }

      const trashInfo = TRASH_TYPES[result.trashType];
      if (!trashInfo) {
        console.error("Unknown trash type:", result.trashType);
        throw new Error("Unknown trash type detected");
      }

      addBotMessage(`✅ Great! I detected ${trashInfo.icon} ${trashInfo.name} (${result.confidence}% confidence).\n\n${result.description}\n\nNow, please share your location or type the place name where you found this trash.`);
      
      setPendingAnalysis({ imageUri, analysis: result });
      setChatState("awaiting_location");
    } catch (error) {
      console.error("Analysis error:", error);
      let errorMessage = "Sorry, I couldn't analyze the image. Please try again.";
      
      if (error instanceof Error) {
        console.error("Error details:", error.message);
        if (error.message.includes("connect") || error.message.includes("network") || error.message.includes("fetch")) {
          errorMessage = "❌ Connection failed. Please check your internet and try again.";
        } else if (error.message.includes("trash type")) {
          errorMessage = "❌ " + error.message + " Please try another photo.";
        } else {
          errorMessage = "❌ Sorry, I couldn't analyze the image. Please try again with a clearer photo of trash.";
        }
      }
      
      addBotMessage(errorMessage);
      setChatState("idle");
    }
  };

  const handleLocationReceived = async (location: { latitude: number; longitude: number; address?: string }) => {
    if (!pendingAnalysis) return;

    setChatState("processing");
    addBotMessage("🎉 Perfect! Processing your submission...");

    // Try to send the photo + location to backend API
    try {
      const resp = await postPhoto({
        uri: pendingAnalysis.imageUri,
        latitude: location.latitude,
        longitude: location.longitude,
        skipDuplicateCheck: false,
      });
      console.log("Backend analysis:", resp);
    } catch (e) {
      console.error("Failed to reach backend API:", e);
      addBotMessage(
        "⚠️ Could not reach backend. Ensure it runs on API_URL and CORS is enabled."
      );
    }

    const trashInfo = TRASH_TYPES[pendingAnalysis.analysis.trashType];
    const scan: ScanResult = {
      id: `scan_${Date.now()}`,
      timestamp: Date.now(),
      imageUri: pendingAnalysis.imageUri,
      trashType: pendingAnalysis.analysis.trashType as TrashType,
      confidence: pendingAnalysis.analysis.confidence,
      pointsEarned: trashInfo.points,
      co2Saved: trashInfo.co2Saved,
    };

    addScan(scan);
    
    setTimeout(() => {
      addBotMessage(`🎊 Awesome! You earned ${trashInfo.points} points and saved ${trashInfo.co2Saved}kg of CO2!\n\nLocation: ${location.address || `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`}\n\nKeep up the great work! Upload another photo to continue helping the planet! 🌍`);
      setPendingAnalysis(null);
      setChatState("idle");
    }, 1000);
  };

  const handleCameraPress = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== "granted") {
        addBotMessage("❌ Camera permission is required to take photos.");
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: "images" as ImagePicker.MediaType,
        allowsEditing: true,
        quality: 0.8,
        base64: Platform.OS === "web" ? false : true,
      });

      if (!result.canceled && result.assets[0]) {
        addUserMessage({ imageUri: result.assets[0].uri });
        await analyzeImage(result.assets[0].uri);
      }
    } catch (error) {
      console.error("Camera error:", error);
      addBotMessage("❌ Failed to open camera. Please try again.");
    }
  };

  const handlePickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: "images" as ImagePicker.MediaType,
        allowsEditing: true,
        quality: 0.8,
        base64: Platform.OS === "web" ? false : true,
      });

      if (!result.canceled && result.assets[0]) {
        addUserMessage({ imageUri: result.assets[0].uri });
        await analyzeImage(result.assets[0].uri);
      }
    } catch (error) {
      console.error("Image picker error:", error);
      addBotMessage("❌ Failed to pick image. Please try again.");
    }
  };

  const handleLocationPress = async () => {
    if (chatState !== "awaiting_location") {
      addBotMessage("📸 Please upload a photo of trash first!");
      return;
    }

    try {
      if (!locationPermission?.granted) {
        const { status } = await requestLocationPermission();
        if (status !== "granted") {
          addBotMessage("❌ Location permission is required. You can also type the place name instead.");
          return;
        }
      }

      addBotMessage("📍 Getting your location...");
      const location = await Location.getCurrentPositionAsync({});
      
      let address = "Unknown location";
      try {
        const [geocode] = await Location.reverseGeocodeAsync({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });
        if (geocode) {
          address = [geocode.street, geocode.city, geocode.country]
            .filter(Boolean)
            .join(", ");
        }
      } catch (e) {
        console.log("Geocoding failed:", e);
      }

      addUserMessage({ 
        location: { 
          latitude: location.coords.latitude, 
          longitude: location.coords.longitude,
          address,
        },
        text: `📍 ${address}`,
      });
      
      await handleLocationReceived({ 
        latitude: location.coords.latitude, 
        longitude: location.coords.longitude,
        address,
      });
    } catch (error) {
      console.error("Location error:", error);
      addBotMessage("❌ Failed to get location. You can type the place name instead.");
    }
  };

  const handleSendText = () => {
    if (!inputText.trim()) return;

    const text = inputText.trim();
    addUserMessage({ text });
    setInputText("");

    if (chatState === "awaiting_location") {
      handleLocationReceived({ 
        latitude: 0, 
        longitude: 0, 
        address: text,
      });
    } else {
      addBotMessage("📸 Please upload a photo of trash to get started!");
    }
  };

  const isInputDisabled = chatState === "analyzing" || chatState === "processing";

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <View style={styles.headerContent}>
          <View style={styles.botAvatar}>
            <Bot size={24} color="#FFFFFF" />
          </View>
          <View>
            <Text style={styles.headerTitle}>EcoRecycle Bot</Text>
            <Text style={styles.headerStatus}>🟢 Online</Text>
          </View>
        </View>
      </View>

      <ScrollView
        ref={scrollViewRef}
        style={styles.chatContainer}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((msg) => (
          <View
            key={msg.id}
            style={[
              styles.messageBubble,
              msg.type === "bot" ? styles.botBubble : styles.userBubble,
            ]}
          >
            {msg.type === "bot" && (
              <View style={styles.botIcon}>
                <Leaf size={16} color={Colors.primary} />
              </View>
            )}
            <View style={[
              styles.bubbleContent,
              msg.type === "bot" ? styles.botBubbleContent : styles.userBubbleContent,
            ]}>
              {msg.imageUri && (
                <Image source={{ uri: msg.imageUri }} style={styles.messageImage} />
              )}
              {msg.text && <Text style={[
                styles.messageText,
                msg.type === "bot" ? styles.botMessageText : styles.userMessageText,
              ]}>{msg.text}</Text>}
            </View>
          </View>
        ))}
      </ScrollView>

      <View style={[styles.inputContainer, { paddingBottom: insets.bottom + 8 }]}>
        <View style={styles.inputRow}>
          <TouchableOpacity 
            style={styles.iconButton} 
            onPress={handleCameraPress}
            disabled={isInputDisabled}
          >
            <Camera size={24} color={isInputDisabled ? "#999" : Colors.primary} />
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.iconButton} 
            onPress={handlePickImage}
            disabled={isInputDisabled}
          >
            <Image 
              source={{ uri: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Ccircle cx='9' cy='9' r='2'/%3E%3Cpath d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/%3E%3C/svg%3E" }}
              style={{ width: 24, height: 24, tintColor: isInputDisabled ? "#999" : Colors.primary }}
            />
          </TouchableOpacity>

          {chatState === "awaiting_location" && (
            <TouchableOpacity 
              style={styles.iconButton} 
              onPress={handleLocationPress}
              disabled={isInputDisabled}
            >
              <MapPin size={24} color={isInputDisabled ? "#999" : Colors.primary} />
            </TouchableOpacity>
          )}

          <TextInput
            style={styles.textInput}
            placeholder={chatState === "awaiting_location" ? "Type place name..." : "Type a message..."}
            placeholderTextColor="#999"
            value={inputText}
            onChangeText={setInputText}
            editable={!isInputDisabled}
            multiline
            maxLength={500}
          />
          
          <TouchableOpacity 
            style={[styles.sendButton, (!inputText.trim() || isInputDisabled) && styles.sendButtonDisabled]} 
            onPress={handleSendText}
            disabled={!inputText.trim() || isInputDisabled}
          >
            <Send size={20} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F0F2F5",
  },
  header: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
  },
  headerContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  botAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: "600" as const,
    color: Colors.text,
  },
  headerStatus: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  chatContainer: {
    flex: 1,
  },
  chatContent: {
    padding: 16,
    gap: 12,
  },
  messageBubble: {
    flexDirection: "row",
    marginBottom: 12,
    maxWidth: "85%",
  },
  botBubble: {
    alignSelf: "flex-start",
  },
  userBubble: {
    alignSelf: "flex-end",
  },
  botIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#E8F5E9",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  bubbleContent: {
    borderRadius: 16,
    padding: 12,
    maxWidth: width * 0.7,
  },
  botBubbleContent: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 4,
  },
  userBubbleContent: {
    backgroundColor: Colors.primary,
    borderTopRightRadius: 4,
  },
  messageImage: {
    width: width * 0.5,
    height: width * 0.5,
    borderRadius: 12,
    marginBottom: 8,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },
  botMessageText: {
    color: Colors.text,
  },
  userMessageText: {
    color: "#FFFFFF",
  },
  inputContainer: {
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#E5E7EB",
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  iconButton: {
    width: 40,
    height: 40,
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 20,
  },
  textInput: {
    flex: 1,
    backgroundColor: "#F0F2F5",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: Colors.text,
    maxHeight: 100,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  sendButtonDisabled: {
    backgroundColor: "#CBD5E0",
  },
});
