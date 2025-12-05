export type TherapistRecommendation = {
  id: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  price: number;
  currency: string;
  recommended: boolean;
  score: number;
  reason: string;
  matchedKeywords: string[];
  avatarUrl?: string;
};

export type TherapistSummary = {
  id: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  price: number;
  currency: string;
  recommended: boolean;
};

export type TherapistDetail = TherapistSummary & {
  biography: string;
  availability: string[];
  recommendationReason?: string;
};

export type TherapistFilters = {
  specialty?: string;
  language?: string;
  recommendedOnly?: boolean;
  minPrice?: number;
  maxPrice?: number;
};
