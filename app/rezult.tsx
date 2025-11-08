import { useLocalSearchParams, router } from "expo-router";
import { Sparkles, Leaf, TrendingUp, ChevronRight } from "lucide-react-native";
import { useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  ScrollView,
} from "react-native";
import Colors from "@/constants/colors";
import { TRASH_TYPES, TrashType } from "@/constants/trash-types";



export default function ResultScreen() {
  const params = useLocalSearchParams<{
    trashType: string;
    confidence: string;
    points: string;
    co2: string;
    description: string;
  }>();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  const trashType = params.trashType as TrashType;
  const trashInfo = TRASH_TYPES[trashType];
  const confidence = parseFloat(params.confidence || "0");
  const points = parseInt(params.points || "0");
  const co2 = parseFloat(params.co2 || "0");

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 500,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Animated.View
          style={[
            styles.iconContainer,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
          <View style={[styles.iconCircle, { backgroundColor: trashInfo.color + "20" }]}>
            <Text style={styles.iconEmoji}>{trashInfo.icon}</Text>
          </View>
          <View style={[styles.badge, { backgroundColor: trashInfo.color }]}>
            <Text style={styles.badgeText}>{Math.round(confidence)}% Match</Text>
          </View>
        </Animated.View>

        <Animated.View style={[styles.content, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
          <Text style={styles.title}>{trashInfo.name}</Text>
          <Text style={styles.description}>{params.description}</Text>

          <View style={styles.statsContainer}>
            <View style={[styles.statCard, styles.statCardPrimary]}>
              <Sparkles size={24} color="#FFFFFF" />
              <Text style={styles.statValue}>+{points}</Text>
              <Text style={styles.statLabel}>Points Earned</Text>
            </View>

            <View style={[styles.statCard, styles.statCardSecondary]}>
              <Leaf size={24} color={Colors.success} />
              <Text style={styles.statValueSecondary}>{co2.toFixed(1)} kg</Text>
              <Text style={styles.statLabelSecondary}>CO₂ Saved</Text>
            </View>
          </View>

          <View style={styles.recyclingInfoCard}>
            <View style={styles.recyclingHeader}>
              <TrendingUp size={20} color={Colors.primary} />
              <Text style={styles.recyclingTitle}>How to Recycle</Text>
            </View>
            <Text style={styles.recyclingInfo}>{trashInfo.recyclingInfo}</Text>
          </View>

          <TouchableOpacity
            style={styles.button}
            onPress={() => router.back()}
            activeOpacity={0.8}
          >
            <Text style={styles.buttonText}>Scan Another Item</Text>
            <ChevronRight size={20} color="#FFFFFF" />
          </TouchableOpacity>
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollContent: {
    padding: 20,
  },
  iconContainer: {
    alignItems: "center",
    marginTop: 40,
    marginBottom: 32,
  },
  iconCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
  },
  iconEmoji: {
    fontSize: 56,
  },
  badge: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  badgeText: {
    fontSize: 14,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  content: {
    gap: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: "700" as const,
    color: Colors.text,
    textAlign: "center",
  },
  description: {
    fontSize: 16,
    color: Colors.textSecondary,
    textAlign: "center",
    lineHeight: 24,
  },
  statsContainer: {
    flexDirection: "row",
    gap: 12,
    marginTop: 8,
  },
  statCard: {
    flex: 1,
    padding: 20,
    borderRadius: 16,
    alignItems: "center",
    gap: 8,
  },
  statCardPrimary: {
    backgroundColor: Colors.primary,
  },
  statCardSecondary: {
    backgroundColor: Colors.surface,
    borderWidth: 2,
    borderColor: Colors.border,
  },
  statValue: {
    fontSize: 28,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  statLabel: {
    fontSize: 13,
    fontWeight: "600" as const,
    color: "#FFFFFF",
    opacity: 0.9,
  },
  statValueSecondary: {
    fontSize: 28,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  statLabelSecondary: {
    fontSize: 13,
    fontWeight: "600" as const,
    color: Colors.textSecondary,
  },
  recyclingInfoCard: {
    backgroundColor: Colors.surface,
    padding: 20,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: Colors.border,
    gap: 12,
  },
  recyclingHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  recyclingTitle: {
    fontSize: 18,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  recyclingInfo: {
    fontSize: 15,
    color: Colors.textSecondary,
    lineHeight: 22,
  },
  button: {
    backgroundColor: Colors.primary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 18,
    borderRadius: 16,
    marginTop: 12,
  },
  buttonText: {
    fontSize: 17,
    fontWeight: "600" as const,
    color: "#FFFFFF",
  },
});
