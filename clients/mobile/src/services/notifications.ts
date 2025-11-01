import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const STORAGE_KEY = "@mindwell/mobile/push-token";
const CACHE_TTL_MS = 1000 * 60 * 60 * 24 * 7; // 7 days

type StoredToken = {
  token: string;
  userId?: string | null;
  registeredAt: number;
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

async function ensureAndroidChannel(): Promise<void> {
  if (Platform.OS !== "android") {
    return;
  }
  await Notifications.setNotificationChannelAsync("mindwell-default", {
    name: "MindWell",
    importance: Notifications.AndroidImportance.DEFAULT,
    sound: "default",
    vibrationPattern: [0, 250, 250, 250],
    enableLights: true,
    lightColor: "#2563EB",
  });
}

async function persistToken(record: StoredToken): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  } catch (error) {
    console.warn("Failed to persist push token", error);
  }
}

export async function getCachedPushToken(): Promise<StoredToken | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as StoredToken;
    if (!parsed.token) {
      return null;
    }
    if (Date.now() - parsed.registeredAt > CACHE_TTL_MS) {
      return null;
    }
    return parsed;
  } catch (error) {
    console.warn("Failed to read cached push token", error);
    return null;
  }
}

async function requestPermissions(): Promise<Notifications.PermissionStatus> {
  const existing = await Notifications.getPermissionsAsync();
  if (existing.status === "granted") {
    return existing.status;
  }
  if (!existing.canAskAgain) {
    return existing.status;
  }
  const requested = await Notifications.requestPermissionsAsync();
  return requested.status;
}

export async function registerDeviceForPush(
  userId: string | null,
): Promise<StoredToken | null> {
  if (!Device.isDevice) {
    console.warn("Push notifications require a physical device.");
    return null;
  }

  const permissionStatus = await requestPermissions();
  if (permissionStatus !== "granted") {
    console.warn("Push notification permission denied:", permissionStatus);
    return null;
  }

  await ensureAndroidChannel();

  try {
    const projectId =
      Constants?.expoConfig?.extra?.eas?.projectId ??
      Constants?.easConfig?.projectId ??
      undefined;

    const token = (
      await Notifications.getExpoPushTokenAsync(
        projectId ? { projectId } : undefined,
      )
    ).data;

    const record: StoredToken = {
      token,
      userId,
      registeredAt: Date.now(),
    };
    await persistToken(record);
    return record;
  } catch (error) {
    console.warn("Failed to register device for push notifications", error);
    return null;
  }
}

export function isPushTokenFresh(
  record: StoredToken | null,
  userId: string | null,
): boolean {
  if (!record || !record.token) {
    return false;
  }
  if (userId && record.userId && record.userId !== userId) {
    return false;
  }
  return Date.now() - record.registeredAt < CACHE_TTL_MS;
}
