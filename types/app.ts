import { TrashType } from "@/constants/trash-types";

export interface ScanResult {
  id: string;
  timestamp: number;
  imageUri: string;
  trashType: TrashType;
  confidence: number;
  pointsEarned: number;
  co2Saved: number;
}

export interface UserStats {
  totalScans: number;
  totalPoints: number;
  totalCo2Saved: number;
  scansByType: Record<TrashType, number>;
  streak: number;
  lastScanDate?: number;
  achievements: Achievement[];
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  unlockedAt?: number;
}

export interface LeaderboardEntry {
  userId: string;
  username: string;
  totalScans: number;
  totalPoints: number;
  rank: number;
  avatarColor: string;
}

export interface User {
  id: string;
  username: string;
  avatarColor: string;
  stats: UserStats;
  scans: ScanResult[];
}
