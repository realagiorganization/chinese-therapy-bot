import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "../locales/en-US.json";
import zh from "../locales/zh-CN.json";

const resources = {
  zh: {
    translation: zh
  },
  en: {
    translation: en
  }
};

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources,
    lng: "zh",
    fallbackLng: "zh",
    interpolation: {
      escapeValue: false
    },
    detection: {
      order: ["htmlTag"]
    }
  });
}

export default i18n;
