import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

interface User {
	id: string;
	email: string;
	name: string;
	role: 'user' | 'admin';
}

interface AuthState {
	user: User | null;
	token: string | null;
	isLoading: boolean;
	isAuthenticated: boolean;
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

// Create the auth store
function createAuthStore() {
	// Initialize state from localStorage if in browser
	const initialState: AuthState = {
		user: null,
		token: null,
		isLoading: false,
		isAuthenticated: false
	};

	if (browser) {
		const storedToken = localStorage.getItem(TOKEN_KEY);
		const storedUser = localStorage.getItem(USER_KEY);

		if (storedToken && storedUser) {
			try {
				initialState.user = JSON.parse(storedUser);
				initialState.token = storedToken;
				initialState.isAuthenticated = true;
			} catch (e) {
				console.error('Failed to parse stored user data');
				localStorage.removeItem(TOKEN_KEY);
				localStorage.removeItem(USER_KEY);
			}
		}
	}

	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		setAuth: (token: string, user: User) => {
			if (browser) {
				localStorage.setItem(TOKEN_KEY, token);
				localStorage.setItem(USER_KEY, JSON.stringify(user));
			}
			set({
				user,
				token,
				isLoading: false,
				isAuthenticated: true
			});
		},

		clearAuth: () => {
			if (browser) {
				localStorage.removeItem(TOKEN_KEY);
				localStorage.removeItem(USER_KEY);
			}
			set({
				user: null,
				token: null,
				isLoading: false,
				isAuthenticated: false
			});
		},

		setLoading: (loading: boolean) => {
			update(state => ({ ...state, isLoading: loading }));
		},

		getToken: (): string | null => {
			if (browser) {
				return localStorage.getItem(TOKEN_KEY);
			}
			return null;
		}
	};
}

export const authStore = createAuthStore();
export const currentUser = derived(authStore, $auth => $auth.user);
export const isAuthenticated = derived(authStore, $auth => $auth.isAuthenticated);
export const authToken = derived(authStore, $auth => $auth.token);

