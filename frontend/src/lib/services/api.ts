import { authStore } from '$lib/stores/auth';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import type { PriorityResponse, WeekData } from '$lib/types/priorities';

export class ApiService {
	public baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
	}

	async healthCheck(): Promise<boolean> {
		try {
			const response = await fetch(`${this.baseUrl}/health`, {
				method: 'GET',
				signal: AbortSignal.timeout(5000)
			});
			return response.ok;
		} catch {
			return false;
		}
	}

	private async request(endpoint: string, options: RequestInit = {}) {
		const config: RequestInit = {
			...options,
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			}
		};

		const response = await fetch(`${this.baseUrl}${endpoint}`, config);

		// Handle 401 Unauthorized - session expired
		if (response.status === 401) {
			authStore.clearAuth();
			if (browser) {
				goto('/login');
			}
			throw new Error('Sitzung abgelaufen. Bitte melden Sie sich erneut an.');
		}

		// Handle 403 Forbidden
		if (response.status === 403) {
			throw new Error('Keine Berechtigung für diese Aktion.');
		}

		// Handle rate limiting
		if (response.status === 429) {
			const data = await response.json();
			throw new Error(data.detail || 'Zu viele Anfragen. Bitte versuchen Sie es später erneut.');
		}

		if (!response.ok) {
			const data = await response.json();
			throw new Error(data.detail || 'Ein Fehler ist aufgetreten');
		}

		return response;
	}

	private async requestJson(endpoint: string, options: RequestInit = {}) {
		const response = await this.request(endpoint, options);
		return response.json();
	}

	// ==================== Authentication ====================

	async login(identity: string, password: string, keepLoggedIn: boolean) {
		const response = await this.requestJson('/auth/login', {
			method: 'POST',
			body: JSON.stringify({
				identity,
				password,
				keep_logged_in: keepLoggedIn
			})
		});

		// Update auth store (cookies are set automatically by server)
		authStore.setAuth(response.security_mode);

		return response;
	}

	async logout() {
		try {
			await this.requestJson('/auth/logout', {
				method: 'POST'
			});
		} catch (error) {
			console.error('Logout error:', error);
		}

		authStore.clearAuth();
	}

	async verify() {
		const response = await this.requestJson('/auth/verify', {
			method: 'GET'
		});
		return response;
	}

	async register(data: {
		identity: string;
		password: string;
		passwordConfirm: string;
		name: string;
		registration_token: string;
		keep_logged_in: boolean;
	}) {
		const response = await this.requestJson('/auth/register', {
			method: 'POST',
			body: JSON.stringify({
				...data
			})
		});

		// Update auth store
		authStore.setAuth();

		return response;
	}

	async changePassword(currentPassword: string, newPassword: string) {
		const response = await this.requestJson('/auth/change-password', {
			method: 'POST',
			body: JSON.stringify({
				current_password: currentPassword,
				new_password: newPassword
			})
		});

		// Password change invalidates all sessions
		authStore.clearAuth();
		if (browser) {
			goto('/login');
		}

		return response;
	}

	// ==================== Account & GDPR ====================

	async getAccountInfo() {
		return this.requestJson('/account/info', {
			method: 'GET'
		});
	}

	async getUserData() {
		return this.requestJson('/account/data', {
			method: 'GET'
		});
	}

	async deleteAllUserData() {
		return this.requestJson('/account/delete', {
			method: 'DELETE'
		});
	}

	// ==================== Priorities ====================

	async getPriorities(month?: string): Promise<PriorityResponse> {
		const endpoint = month ? `/priorities/${month}` : '/priorities';
		return this.requestJson(endpoint, {
			method: 'GET'
		});
	}

	async updatePriority(month: string, priorityData: WeekData[]) {
		return this.requestJson(`/priorities/${month}`, {
			method: 'PUT',
			body: JSON.stringify(priorityData)
		});
	}

	// ==================== Admin Endpoints ====================

	async getMagicWordInfo() {
		return this.requestJson('/admin/magic-word-info', {
			method: 'GET'
		});
	}

	async updateMagicWord(newMagicWord: string) {
		return this.requestJson('/admin/update-magic-word', {
			method: 'POST',
			body: JSON.stringify({ new_magic_word: newMagicWord })
		});
	}

	async getUserSubmissions(month: string) {
		return this.requestJson(`/admin/users/${month}`, {
			method: 'GET'
		});
	}
}

export const apiService = new ApiService();
