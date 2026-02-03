export interface VentureBuilder {
    id: number;
    name: string;
    fullName: string;
    profileImage: string;
    image: string;
    domain: string;
    bio: string;
    expertise: string;
  }
  
  export interface CalendarDay {
    day: number | string;
    empty?: boolean;
    date?: Date;
    dateString?: string;
  }