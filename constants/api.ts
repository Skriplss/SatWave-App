import { Platform } from "react-native";

// Prefer EXPO_PUBLIC_API_URL when provided at build/runtime
const envUrl = process.env.EXPO_PUBLIC_API_URL;

let inferredDefault = "http://localhost:8000";

// On Android emulator, localhost is 10.0.2.2
if (Platform.OS === "android") {
  inferredDefault = "http://10.0.2.2:8000";
}

// On web, prefer current host with port 8000
if (Platform.OS === "web" && typeof window !== "undefined") {
  const { protocol, hostname } = window.location;
  inferredDefault = `${protocol}//${hostname}:8000`;
}

export const API_URL = envUrl || inferredDefault;

