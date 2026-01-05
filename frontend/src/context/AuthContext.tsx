import { createContext, useContext } from "react";

export interface AuthUser {
  id: number;
  email: string;
  nickname?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  setUser: (u: AuthUser | null) => void;
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  setUser: () => {},
});

export const useAuth = () => useContext(AuthContext);
