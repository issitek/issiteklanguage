import { defineStore } from "pinia";
import {
  api,
  clearTokens,
  hasToken,
  rawRefreshToken,
  setTokens,
  type User,
} from "../api";

export const useAuth = defineStore("auth", {
  state: () => ({
    user: null as User | null,
    ready: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
  },
  actions: {
    async bootstrap() {
      if (!hasToken()) {
        this.ready = true;
        return;
      }
      try {
        this.user = await api.me();
      } catch {
        clearTokens();
        this.user = null;
      } finally {
        this.ready = true;
      }
    },

    async login(email: string, password: string) {
      const tokens = await api.login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      this.user = await api.me();
    },

    async register(email: string, password: string, displayName: string) {
      const tokens = await api.register(email, password, displayName);
      setTokens(tokens.access_token, tokens.refresh_token);
      this.user = await api.me();
    },

    async logout() {
      const refresh = rawRefreshToken();
      if (refresh) {
        try {
          await api.logout(refresh);
        } catch {
          // La sesión local se cierra igual.
        }
      }
      clearTokens();
      this.user = null;
    },
  },
});
