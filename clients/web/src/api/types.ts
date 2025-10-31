export type TherapistSummary = {
  id: string;
  name: string;
  title: string;
  specialties: string[];
  languages: string[];
  price: number;
  currency?: string;
  recommended: boolean;
  availability: string[];
};

export type TherapistFilters = {
  specialty?: string;
  language?: string;
  recommendedOnly?: boolean;
  maxPrice?: number;
};
