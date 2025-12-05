export const VOICE_RATE_PRESETS = [
  { id: "slow", labelZh: "慢速", labelEn: "Slow", value: 0.85 },
  { id: "standard", labelZh: "标准", labelEn: "Standard", value: 1 },
  { id: "fast", labelZh: "快速", labelEn: "Fast", value: 1.2 },
] as const;

export const VOICE_PITCH_PRESETS = [
  { id: "warm", labelZh: "柔和", labelEn: "Warm", value: 0.9 },
  { id: "standard", labelZh: "标准", labelEn: "Standard", value: 1 },
  { id: "bright", labelZh: "明亮", labelEn: "Bright", value: 1.1 },
] as const;
