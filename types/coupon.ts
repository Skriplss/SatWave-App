export type Coupon = {
  id: string;
  title: string;
  description?: string | null;
  discount_percent?: number | null;
  code?: string | null;
  expires_at?: string | null;
  url?: string | null;
  image_url?: string | null;
};
