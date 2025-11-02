import {
  getCachedPushToken,
  isPushTokenFresh,
  registerDeviceForPush,
} from "@services/notifications";
import { useEffect, useState } from "react";

type RegistrationStatus = "idle" | "registering" | "granted" | "denied";

type UsePushNotificationsResult = {
  token: string | null;
  status: RegistrationStatus;
};

export function usePushNotifications(
  userId: string | null,
): UsePushNotificationsResult {
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<RegistrationStatus>("idle");

  useEffect(() => {
    let isActive = true;

    const bootstrap = async () => {
      if (!userId) {
        if (isActive) {
          setToken(null);
          setStatus("idle");
        }
        return;
      }

      setStatus("registering");

      const cached = await getCachedPushToken();
      if (isActive && isPushTokenFresh(cached, userId)) {
        setToken(cached?.token ?? null);
        setStatus("granted");
      }

      const registration = await registerDeviceForPush(userId);
      if (!isActive) {
        return;
      }

      if (registration) {
        setToken(registration.token);
        setStatus("granted");
      } else if (!cached) {
        setStatus("denied");
      }
    };

    bootstrap().catch((error) => {
      console.warn("Failed to register push notifications", error);
      if (isActive) {
        setStatus("denied");
      }
    });

    return () => {
      isActive = false;
    };
  }, [userId]);

  return { token, status };
}
