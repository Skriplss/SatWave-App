import { Trophy, Medal, Crown } from "lucide-react-native";
import { View, Text, StyleSheet, ScrollView, Animated } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useApp, useUserRank } from "@/contexts/app-context";
import Colors from "@/constants/colors";

export default function LeaderboardScreen() {
  const insets = useSafeAreaInsets();
  const { leaderboard, user } = useApp();
  const userRank = useUserRank();

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Crown size={24} color="#FFD700" />;
    if (rank === 2) return <Medal size={24} color="#C0C0C0" />;
    if (rank === 3) return <Medal size={24} color="#CD7F32" />;
    return null;
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 24 }]}>
        <Trophy size={32} color={Colors.primary} />
        <Text style={styles.headerTitle}>Leaderboard</Text>
        <Text style={styles.headerSubtitle}>Top eco-warriors worldwide</Text>
      </View>

      {userRank && (
        <View style={[styles.userRankCard, { borderColor: user?.avatarColor || Colors.primary }]}>
          <View style={styles.rankBadge}>
            <Text style={styles.rankText}>#{userRank}</Text>
          </View>
          <View style={styles.userRankInfo}>
            <Text style={styles.userRankName}>Your Rank</Text>
            <Text style={styles.userRankPoints}>{user?.stats.totalPoints} points</Text>
          </View>
        </View>
      )}

      <ScrollView style={styles.listContainer} contentContainerStyle={styles.listContent}>
        {leaderboard.map((entry, index) => {
          const isCurrentUser = entry.userId === user?.id;
          const animatedValue = new Animated.Value(0);

          Animated.timing(animatedValue, {
            toValue: 1,
            duration: 300,
            delay: index * 50,
            useNativeDriver: true,
          }).start();

          return (
            <Animated.View
              key={entry.userId}
              style={[
                styles.leaderboardItem,
                isCurrentUser && styles.currentUserItem,
                { opacity: animatedValue },
              ]}
            >
              <View style={styles.rankSection}>
                {getRankIcon(entry.rank) || (
                  <Text style={styles.rankNumber}>#{entry.rank}</Text>
                )}
              </View>

              <View style={[styles.avatar, { backgroundColor: entry.avatarColor }]}>
                <Text style={styles.avatarText}>
                  {entry.username.substring(0, 2).toUpperCase()}
                </Text>
              </View>

              <View style={styles.userInfo}>
                <Text style={styles.username} numberOfLines={1}>
                  {entry.username}
                  {isCurrentUser && <Text style={styles.youBadge}> (You)</Text>}
                </Text>
                <Text style={styles.scans}>{entry.totalScans} scans</Text>
              </View>

              <View style={styles.pointsContainer}>
                <Text style={styles.points}>{entry.totalPoints}</Text>
                <Text style={styles.pointsLabel}>pts</Text>
              </View>
            </Animated.View>
          );
        })}

        {leaderboard.length === 0 && (
          <View style={styles.emptyState}>
            <Trophy size={64} color={Colors.textLight} />
            <Text style={styles.emptyText}>No rankings yet</Text>
            <Text style={styles.emptySubtext}>Be the first to scan and earn points!</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    alignItems: "center",
    paddingVertical: 24,
    paddingHorizontal: 20,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "700" as const,
    color: Colors.text,
    marginTop: 8,
  },
  headerSubtitle: {
    fontSize: 14,
    color: Colors.textSecondary,
    marginTop: 4,
  },
  userRankCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    margin: 16,
    padding: 16,
    borderRadius: 16,
    borderWidth: 2,
    gap: 16,
  },
  rankBadge: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
  },
  rankText: {
    fontSize: 20,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  userRankInfo: {
    flex: 1,
  },
  userRankName: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.text,
    marginBottom: 4,
  },
  userRankPoints: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  listContainer: {
    flex: 1,
  },
  listContent: {
    padding: 16,
    gap: 12,
  },
  leaderboardItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    padding: 16,
    borderRadius: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  currentUserItem: {
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  rankSection: {
    width: 32,
    alignItems: "center",
  },
  rankNumber: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.textSecondary,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
  },
  avatarText: {
    fontSize: 18,
    fontWeight: "700" as const,
    color: "#FFFFFF",
  },
  userInfo: {
    flex: 1,
  },
  username: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: Colors.text,
    marginBottom: 4,
  },
  youBadge: {
    color: Colors.primary,
    fontWeight: "700" as const,
  },
  scans: {
    fontSize: 13,
    color: Colors.textSecondary,
  },
  pointsContainer: {
    alignItems: "flex-end",
  },
  points: {
    fontSize: 20,
    fontWeight: "700" as const,
    color: Colors.primary,
  },
  pointsLabel: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 64,
    gap: 12,
  },
  emptyText: {
    fontSize: 20,
    fontWeight: "600" as const,
    color: Colors.textSecondary,
  },
  emptySubtext: {
    fontSize: 15,
    color: Colors.textLight,
  },
});
