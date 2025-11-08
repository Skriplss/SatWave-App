import { User, Settings, Award, TrendingUp, Leaf, Flame } from "lucide-react-native";
import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Modal,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useApp } from "@/contexts/app-context";
import Colors from "@/constants/colors";
import { TRASH_TYPES } from "@/constants/trash-types";

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const { user, updateUsername } = useApp();
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [newUsername, setNewUsername] = useState(user?.username || "");

  if (!user) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  const handleSaveUsername = () => {
    if (newUsername.trim()) {
      updateUsername(newUsername.trim());
    }
    setEditModalVisible(false);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={[styles.scrollContent, { paddingTop: insets.top + 20 }]}>
        <View style={styles.profileHeader}>
          <View style={[styles.avatar, { backgroundColor: user.avatarColor }]}>
            <User size={48} color="#FFFFFF" />
          </View>
          <Text style={styles.username}>{user.username}</Text>
          <TouchableOpacity
            style={styles.editButton}
            onPress={() => {
              setNewUsername(user.username);
              setEditModalVisible(true);
            }}
          >
            <Settings size={18} color={Colors.primary} />
            <Text style={styles.editButtonText}>Edit Profile</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <TrendingUp size={28} color={Colors.primary} />
            <Text style={styles.statValue}>{user.stats.totalScans}</Text>
            <Text style={styles.statLabel}>Total Scans</Text>
          </View>

          <View style={styles.statBox}>
            <Award size={28} color={Colors.accent} />
            <Text style={styles.statValue}>{user.stats.totalPoints}</Text>
            <Text style={styles.statLabel}>Points</Text>
          </View>

          <View style={styles.statBox}>
            <Leaf size={28} color={Colors.success} />
            <Text style={styles.statValue}>{user.stats.totalCo2Saved.toFixed(1)}</Text>
            <Text style={styles.statLabel}>kg CO₂ Saved</Text>
          </View>

          <View style={styles.statBox}>
            <Flame size={28} color={Colors.error} />
            <Text style={styles.statValue}>{user.stats.streak}</Text>
            <Text style={styles.statLabel}>Day Streak</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Scans by Type</Text>
          {Object.entries(TRASH_TYPES).map(([key, info]) => {
            const count = user.stats.scansByType[key as keyof typeof TRASH_TYPES] || 0;
            if (count === 0) return null;

            return (
              <View key={key} style={styles.typeRow}>
                <Text style={styles.typeIcon}>{info.icon}</Text>
                <Text style={styles.typeName}>{info.name}</Text>
                <View style={styles.typeCountBadge}>
                  <Text style={styles.typeCount}>{count}</Text>
                </View>
              </View>
            );
          })}

          {Object.keys(user.stats.scansByType).length === 0 && (
            <Text style={styles.emptyText}>No scans yet. Start scanning to see stats!</Text>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Achievements</Text>
          <View style={styles.achievementsGrid}>
            {user.stats.achievements.map((achievement) => (
              <View key={achievement.id} style={styles.achievementCard}>
                <Text style={styles.achievementIcon}>{achievement.icon}</Text>
                <Text style={styles.achievementName}>{achievement.name}</Text>
                <Text style={styles.achievementDesc} numberOfLines={2}>
                  {achievement.description}
                </Text>
              </View>
            ))}
          </View>

          {user.stats.achievements.length === 0 && (
            <Text style={styles.emptyText}>
              Complete scans to unlock achievements!
            </Text>
          )}
        </View>
      </ScrollView>

      <Modal
        visible={editModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setEditModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Username</Text>
            <TextInput
              style={styles.input}
              value={newUsername}
              onChangeText={setNewUsername}
              placeholder="Enter new username"
              placeholderTextColor={Colors.textLight}
              autoFocus
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setEditModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.saveButton]}
                onPress={handleSaveUsername}
              >
                <Text style={styles.saveButtonText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingText: {
    fontSize: 16,
    color: Colors.textSecondary,
    textAlign: "center",
    marginTop: 40,
  },
  scrollContent: {
    padding: 20,
    gap: 24,
  },
  profileHeader: {
    alignItems: "center",
    paddingVertical: 32,
    gap: 12,
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    justifyContent: "center",
    alignItems: "center",
  },
  username: {
    fontSize: 24,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  editButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  editButtonText: {
    fontSize: 14,
    fontWeight: "600" as const,
    color: Colors.primary,
  },
  statsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  statBox: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: Colors.surface,
    padding: 20,
    borderRadius: 16,
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  statValue: {
    fontSize: 28,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  statLabel: {
    fontSize: 13,
    color: Colors.textSecondary,
    fontWeight: "600" as const,
  },
  section: {
    gap: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700" as const,
    color: Colors.text,
  },
  typeRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    padding: 16,
    borderRadius: 12,
    gap: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  typeIcon: {
    fontSize: 28,
  },
  typeName: {
    flex: 1,
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.text,
  },
  typeCountBadge: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  typeCount: {
    fontSize: 14,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  achievementsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  achievementCard: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: Colors.surface,
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  achievementIcon: {
    fontSize: 40,
  },
  achievementName: {
    fontSize: 14,
    fontWeight: "700" as const,
    color: Colors.text,
    textAlign: "center",
  },
  achievementDesc: {
    fontSize: 12,
    color: Colors.textSecondary,
    textAlign: "center",
  },
  emptyText: {
    fontSize: 14,
    color: Colors.textLight,
    textAlign: "center",
    paddingVertical: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  modalContent: {
    backgroundColor: Colors.surface,
    borderRadius: 20,
    padding: 24,
    width: "100%",
    maxWidth: 400,
    gap: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "700" as const,
    color: Colors.text,
    textAlign: "center",
  },
  input: {
    backgroundColor: Colors.background,
    borderWidth: 2,
    borderColor: Colors.border,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: Colors.text,
  },
  modalButtons: {
    flexDirection: "row",
    gap: 12,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },
  cancelButton: {
    backgroundColor: Colors.background,
    borderWidth: 2,
    borderColor: Colors.border,
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.text,
  },
  saveButton: {
    backgroundColor: Colors.primary,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: "#FFFFFF",
  },
});
