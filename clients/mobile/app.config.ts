import type { ExpoConfig, ConfigContext } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "MindWell Mobile",
  slug: "mindwell-mobile",
  version: "0.1.0",
  orientation: "portrait",
  userInterfaceStyle: "light",
  extra: {
    apiBaseUrl:
      process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api",
    speechRegion: process.env.EXPO_PUBLIC_SPEECH_REGION ?? "eastasia",
  },
  ios: {
    supportsTablet: false,
    bundleIdentifier: "com.mindwell.mobile",
    infoPlist: {
      UIBackgroundModes: ["remote-notification"],
    },
  },
  android: {
    package: "com.mindwell.mobile",
  },
  plugins: ["expo-notifications"],
  experiments: {
    typedRoutes: false,
  },
});
