export type Gender = 'MEN' | 'WOMEN' | 'KIDS';

export interface GarmentOption {
  id: string;
  label: string;
  emoji: string;
  tagline: string;
}

export interface StyleOption {
  id: string;
  label: string;
  emoji: string;
}

export interface GarmentDefinition {
  id: string;
  label: string;
  emoji: string;
  tagline: string;
  styles: StyleOption[];
}

export const genders: { id: Gender; label: string; emoji: string; tagline: string }[] = [
  { id: 'MEN', label: 'Men', emoji: '👔', tagline: 'Shirts, pants & more' },
  { id: 'WOMEN', label: 'Women', emoji: '🥻', tagline: 'Sarees, suits & more' },
  { id: 'KIDS', label: 'Kids', emoji: '🧒', tagline: 'Comfortable playwear' },
];

export const garmentsByGender: Record<Gender, GarmentOption[]> = {
  MEN: [
    { id: 'shirt', label: 'Shirt', emoji: '👔', tagline: 'Classic or fitted' },
    { id: 't_shirt', label: 'T-Shirt', emoji: '👕', tagline: 'Casual & easy' },
    { id: 'kurta', label: 'Kurta', emoji: '🧥', tagline: 'Ethnic comfort' },
    { id: 'pant', label: 'Pant / Trousers', emoji: '👖', tagline: 'Everyday & formal' },
    { id: 'jeans', label: 'Jeans', emoji: '👖', tagline: 'Durable denim' },
    { id: 'jacket', label: 'Jacket', emoji: '🧥', tagline: 'Layered style' },
    { id: 'suit', label: 'Suit', emoji: '🤵', tagline: 'Sharp & formal' },
  ],
  WOMEN: [
    { id: 'saree', label: 'Saree', emoji: '🥻', tagline: 'Elegant drape' },
    { id: 'blouse', label: 'Blouse', emoji: '👚', tagline: 'Top & choli' },
    { id: 'kurti', label: 'Kurti', emoji: '👗', tagline: 'Daily elegance' },
    { id: 'salwar_suit', label: 'Salwar Suit', emoji: '🥻', tagline: 'Traditional set' },
    { id: 'palazzo', label: 'Palazzo', emoji: '👖', tagline: 'Flow & comfort' },
    { id: 'pant', label: 'Pant / Trousers', emoji: '👖', tagline: 'Modern fits' },
    { id: 'jeans', label: 'Jeans', emoji: '👖', tagline: 'Classic denim' },
    { id: 'top', label: 'Top', emoji: '👚', tagline: 'Trendy styles' },
    { id: 'dress', label: 'Dress', emoji: '👗', tagline: 'One-piece chic' },
    { id: 'lehenga', label: 'Lehenga', emoji: '👗', tagline: 'Festive glamour' },
    { id: 'dupatta', label: 'Dupatta', emoji: '🧣', tagline: 'Drape & style' },
    { id: 'jacket', label: 'Jacket', emoji: '🧥', tagline: 'Trendy layer' },
  ],
  KIDS: [
    { id: 'shirt', label: 'Shirt', emoji: '👔', tagline: 'Neat & tidy' },
    { id: 't_shirt', label: 'T-Shirt', emoji: '👕', tagline: 'Play-friendly' },
    { id: 'kurta', label: 'Kurta', emoji: '🧥', tagline: 'Festive wear' },
    { id: 'pant', label: 'Pant', emoji: '👖', tagline: 'Durable & comfy' },
    { id: 'dress', label: 'Dress', emoji: '👗', tagline: 'Cute & comfy' },
    { id: 'frock', label: 'Frock', emoji: '🎀', tagline: 'Sweet & bright' },
    { id: 'ethnic_wear', label: 'Ethnic Wear', emoji: '🥻', tagline: 'Tradition for kids' },
  ],
};

export const garmentStyles: Record<string, StyleOption[]> = {
  DEFAULT: [
    { id: 'regular', label: 'Regular Fit', emoji: '🙂' },
    { id: 'slim', label: 'Slim Fit', emoji: '✨' },
    { id: 'oversized', label: 'Oversized', emoji: '🟦' },
  ],
  shirt: [
    { id: 'classic', label: 'Classic Shirt', emoji: '👔' },
    { id: 'slim', label: 'Slim Fit', emoji: '🧵' },
    { id: 'regular', label: 'Regular Fit', emoji: '🙂' },
    { id: 'oversized', label: 'Oversized', emoji: '🟦' },
  ],
  t_shirt: [
    { id: 'classic', label: 'Classic Tee', emoji: '👕' },
    { id: 'slim', label: 'Slim Fit', emoji: '✨' },
    { id: 'oversized', label: 'Oversized', emoji: '🟦' },
  ],
  kurta: [
    { id: 'straight', label: 'Straight', emoji: '📏' },
    { id: 'a_line', label: 'A-Line', emoji: '🎨' },
    { id: 'pathani', label: 'Pathani', emoji: '🧥' },
  ],
  pant: [
    { id: 'regular', label: 'Regular Fit', emoji: '🙂' },
    { id: 'slim', label: 'Slim Fit', emoji: '✨' },
    { id: 'straight', label: 'Straight Fit', emoji: '📏' },
    { id: 'formal', label: 'Formal Trouser', emoji: '🤵' },
    { id: 'casual', label: 'Casual Pant', emoji: '👖' },
    { id: 'cargo', label: 'Cargo', emoji: '🎒' },
  ],
  jeans: [
    { id: 'slim', label: 'Slim Fit', emoji: '✨' },
    { id: 'straight', label: 'Straight Fit', emoji: '📏' },
    { id: 'bootcut', label: 'Bootcut', emoji: '👢' },
    { id: 'baggy', label: 'Baggy', emoji: '🟦' },
  ],
  jacket: [
    { id: 'blazer', label: 'Blazer', emoji: '🤵' },
    { id: 'denim', label: 'Denim Jacket', emoji: '👖' },
    { id: 'bomber', label: 'Bomber', emoji: '✈️' },
    { id: 'hooded', label: 'Hooded', emoji: '🧥' },
  ],
  suit: [
    { id: 'slim', label: 'Slim Fit', emoji: '✨' },
    { id: 'regular', label: 'Regular Fit', emoji: '🙂' },
    { id: 'classic_tailored', label: 'Tailored', emoji: '🎩' },
  ],
  saree: [
    { id: 'traditional', label: 'Traditional Draping', emoji: '🥻' },
    { id: 'modern', label: 'Modern Draping', emoji: '✨' },
    { id: 'party', label: 'Party Draping', emoji: '🎉' },
  ],
  blouse: [
    { id: 'round_neck', label: 'Round Neck', emoji: '⭕' },
    { id: 'v_neck', label: 'V Neck', emoji: '🔽' },
    { id: 'boat_neck', label: 'Boat Neck', emoji: '⛵' },
    { id: 'designer', label: 'Designer', emoji: '💎' },
  ],
  kurti: [
    { id: 'straight', label: 'Straight', emoji: '📏' },
    { id: 'a_line', label: 'A-Line', emoji: '🎨' },
    { id: 'anarkali', label: 'Anarkali', emoji: '👗' },
    { id: 'short_kurti', label: 'Short Kurti', emoji: '✂️' },
  ],
  salwar_suit: [
    { id: 'straight_suit', label: 'Straight Suit', emoji: '📏' },
    { id: 'a_line', label: 'A-Line', emoji: '🎨' },
    { id: 'anarkali', label: 'Anarkali', emoji: '👗' },
  ],
  palazzo: [
    { id: 'regular', label: 'Regular', emoji: '🙂' },
    { id: 'wide_leg', label: 'Wide Leg', emoji: '🟦' },
    { id: 'flared', label: 'Flared', emoji: '🌀' },
  ],
  top: [
    { id: 'crop', label: 'Crop Top', emoji: '✂️' },
    { id: 'peplum', label: 'Peplum', emoji: '🌸' },
    { id: 'tunic', label: 'Tunic', emoji: '👚' },
    { id: 'collar', label: 'Collared', emoji: '👔' },
  ],
  dress: [
    { id: 'bodycon', label: 'Bodycon', emoji: '🤍' },
    { id: 'a_line', label: 'A-Line', emoji: '🎨' },
    { id: 'maxi', label: 'Maxi', emoji: '👗' },
    { id: 'wrap', label: 'Wrap', emoji: '🎀' },
  ],
  lehenga: [
    { id: 'traditional', label: 'Traditional', emoji: '🥻' },
    { id: 'bridal', label: 'Bridal', emoji: '💍' },
    { id: 'modern', label: 'Modern', emoji: '✨' },
  ],
  dupatta: [
    { id: 'classic_drape', label: 'Classic Drape', emoji: '🧣' },
    { id: 'open_drape', label: 'Open Drape', emoji: '✨' },
    { id: 'one_shoulder', label: 'One Shoulder', emoji: '➡️' },
  ],
  frock: [
    { id: 'a_line', label: 'A-Line', emoji: '🎨' },
    { id: 'tiered', label: 'Tiered', emoji: '🍰' },
    { id: 'empire', label: 'Empire Waist', emoji: '👑' },
  ],
  ethnic_wear: [
    { id: 'kurta_set', label: 'Kurta Set', emoji: '🧥' },
    { id: 'dhoti_set', label: 'Dhoti Set', emoji: '🪔' },
    { id: 'ethnic_dress', label: 'Ethnic Dress', emoji: '👗' },
  ],
};

export function stylesForGarment(garmentId: string): StyleOption[] {
  return garmentStyles[garmentId] ?? garmentStyles.DEFAULT;
}

export const bottomNav = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'tryon', label: 'Try On', icon: 'sparkles', primary: true },
  { id: 'history', label: 'History', icon: 'time' },
  { id: 'profile', label: 'Profile', icon: 'person' },
] as const;
