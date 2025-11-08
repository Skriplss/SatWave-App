import AsyncStorage from "@react-native-async-storage/async-storage";
import createContextHook from "@nkzw/create-context-hook";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useMemo, useCallback } from "react";
import { User, ScanResult, LeaderboardEntry, Achievement } from "@/types/app";
import { TrashType, TRASH_TYPES } from "@/constants/trash-types";

const STORAGE_KEY = "ecorecycle_user";
const LEADERBOARD_KEY = "ecorecycle_leaderboard";

const ACHIEVEMENTS_DEFINITIONS: Achievement[] = [
  { id: "first_scan", name: "First Step", description: "Complete your first scan", icon: "🎯" },
  { id: "10_scans", name: "Getting Started", description: "Complete 10 scans", icon: "🌱" },
  { id: "50_scans", name: "Eco Warrior", description: "Complete 50 scans", icon: "🌿" },
  { id: "100_scans", name: "Planet Protector", description: "Complete 100 scans", icon: "🌍" },
  { id: "streak_7", name: "Week Streak", description: "Scan for 7 days in a row", icon: "🔥" },
  { id: "all_types", name: "Recycling Master", description: "Scan all trash types", icon: "♻️" },
];

function generateAvatarColor(): string {
  const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];
  return colors[Math.floor(Math.random() * colors.length)];
}

function generateUsername(): string {
  const adjectives = ["Eco", "Green", "Planet", "Earth", "Nature", "Clean"];
  const nouns = ["Hero", "Warrior", "Guardian", "Saver", "Friend", "Champion"];
  return `${adjectives[Math.floor(Math.random() * adjectives.length)]}${nouns[Math.floor(Math.random() * nouns.length)]}${Math.floor(Math.random() * 9999)}`;
}

function calculateStreak(scans: ScanResult[]): number {
  if (scans.length === 0) return 0;

  const sortedScans = [...scans].sort((a, b) => b.timestamp - a.timestamp);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  let streak = 0;
  let currentDate = today.getTime();

  for (const scan of sortedScans) {
    const scanDate = new Date(scan.timestamp);
    scanDate.setHours(0, 0, 0, 0);

    if (scanDate.getTime() === currentDate) {
      streak++;
      currentDate -= 24 * 60 * 60 * 1000;
    } else if (scanDate.getTime() < currentDate) {
      break;
    }
  }

  return streak;
}

export const [AppProvider, useApp] = createContextHook(() => {
  const queryClient = useQueryClient();
  const [localUser, setLocalUser] = useState<User | null>(null);

  const userQuery = useQuery({
    queryKey: ["user"],
    queryFn: async (): Promise<User> => {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }

      const newUser: User = {
        id: `user_${Date.now()}`,
        username: generateUsername(),
        avatarColor: generateAvatarColor(),
        stats: {
          totalScans: 0,
          totalPoints: 0,
          totalCo2Saved: 0,
          scansByType: {} as Record<TrashType, number>,
          streak: 0,
          achievements: [],
        },
        scans: [],
      };

      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
      return newUser;
    },
  });

  const leaderboardQuery = useQuery({
    queryKey: ["leaderboard"],
    queryFn: async (): Promise<LeaderboardEntry[]> => {
      const stored = await AsyncStorage.getItem(LEADERBOARD_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
      return [];
    },
  });

  useEffect(() => {
    if (userQuery.data) {
      setLocalUser(userQuery.data);
    }
  }, [userQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async (user: User) => {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(user));
      return user;
    },
    onSuccess: (user) => {
      queryClient.setQueryData(["user"], user);
      setLocalUser(user);
    },
  });

  const updateLeaderboardMutation = useMutation({
    mutationFn: async (user: User) => {
      let leaderboard = await AsyncStorage.getItem(LEADERBOARD_KEY);
      let entries: LeaderboardEntry[] = leaderboard ? JSON.parse(leaderboard) : [];

      const existingIndex = entries.findIndex((e) => e.userId === user.id);
      const entry: LeaderboardEntry = {
        userId: user.id,
        username: user.username,
        totalScans: user.stats.totalScans,
        totalPoints: user.stats.totalPoints,
        rank: 0,
        avatarColor: user.avatarColor,
      };

      if (existingIndex >= 0) {
        entries[existingIndex] = entry;
      } else {
        entries.push(entry);
      }

      entries.sort((a, b) => b.totalPoints - a.totalPoints);
      entries = entries.map((e, i) => ({ ...e, rank: i + 1 }));

      await AsyncStorage.setItem(LEADERBOARD_KEY, JSON.stringify(entries));
      return entries;
    },
    onSuccess: (entries) => {
      queryClient.setQueryData(["leaderboard"], entries);
    },
  });

  const saveMutate = saveMutation.mutate;
  const updateLeaderboardMutate = updateLeaderboardMutation.mutate;

  const addScan = useCallback((scan: ScanResult) => {
    if (!localUser) return;

    const updatedScans = [...localUser.scans, scan];
    const scansByType = { ...localUser.stats.scansByType };
    scansByType[scan.trashType] = (scansByType[scan.trashType] || 0) + 1;

    const totalScans = updatedScans.length;
    const totalPoints = localUser.stats.totalPoints + scan.pointsEarned;
    const totalCo2Saved = localUser.stats.totalCo2Saved + scan.co2Saved;
    const streak = calculateStreak(updatedScans);

    const achievements = [...localUser.stats.achievements];
    const checkAchievement = (id: string) => {
      if (!achievements.find((a) => a.id === id)) {
        const def = ACHIEVEMENTS_DEFINITIONS.find((a) => a.id === id);
        if (def) {
          achievements.push({ ...def, unlockedAt: Date.now() });
        }
      }
    };

    if (totalScans === 1) checkAchievement("first_scan");
    if (totalScans === 10) checkAchievement("10_scans");
    if (totalScans === 50) checkAchievement("50_scans");
    if (totalScans === 100) checkAchievement("100_scans");
    if (streak === 7) checkAchievement("streak_7");
    if (Object.keys(scansByType).length === Object.keys(TRASH_TYPES).length) {
      checkAchievement("all_types");
    }

    const updatedUser: User = {
      ...localUser,
      scans: updatedScans,
      stats: {
        ...localUser.stats,
        totalScans,
        totalPoints,
        totalCo2Saved,
        scansByType,
        streak,
        lastScanDate: scan.timestamp,
        achievements,
      },
    };

    saveMutate(updatedUser);
    updateLeaderboardMutate(updatedUser);
  }, [localUser, saveMutate, updateLeaderboardMutate]);

  const updateUsername = useCallback((username: string) => {
    if (!localUser) return;
    const updatedUser = { ...localUser, username };
    saveMutate(updatedUser);
    updateLeaderboardMutate(updatedUser);
  }, [localUser, saveMutate, updateLeaderboardMutate]);

  return useMemo(() => ({
    user: localUser,
    leaderboard: leaderboardQuery.data || [],
    addScan,
    updateUsername,
    isLoading: userQuery.isLoading,
  }), [localUser, leaderboardQuery.data, addScan, updateUsername, userQuery.isLoading]);
});

export function useUserRank() {
  const { user, leaderboard } = useApp();
  return useMemo(() => {
    if (!user) return null;
    const entry = leaderboard.find((e) => e.userId === user.id);
    return entry?.rank || null;
  }, [user, leaderboard]);
}
