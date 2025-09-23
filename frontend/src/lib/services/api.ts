import type { AnalysisResult } from '../types/scanner';

export class ApiService {
	private baseUrl: string;
	private timeout: number;

	constructor(baseUrl: string = '/api', timeout: number = 30000) {
		this.baseUrl = baseUrl;
		this.timeout = timeout;
	}

	async analyzeSchedule(imageBlob: Blob): Promise<AnalysisResult> {
		const formData = new FormData();
		formData.append('image', imageBlob, 'capture.jpg');

		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), this.timeout);

		try {
			const response = await fetch(`${this.baseUrl}/analyze-schedule`, {
				method: 'POST',
				body: formData,
				signal: controller.signal
			});

			clearTimeout(timeoutId);

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Server error (${response.status}): ${errorText}`);
			}

			const result = await response.json();
			return this.validateAnalysisResult(result);
		} catch (error) {
			clearTimeout(timeoutId);
			const e = error as Error; // Type assertion
			if (e.name === 'AbortError') {
				throw new Error('Request timeout - analysis took too long');
			}

			throw e;
		}
	}

	private validateAnalysisResult(result: any): AnalysisResult {
		// Validate the result structure
		if (!result || typeof result !== 'object') {
			throw new Error('Invalid response format');
		}

		// Ensure required fields exist
		const validated: AnalysisResult = {
			success: Boolean(result.success),
			analysis: result.analysis || undefined,
			error: result.error || undefined
		};

		// Validate analysis structure if present
		if (validated.analysis) {
			validated.analysis = {
				labels: Array.isArray(result.analysis.labels) ? result.analysis.labels : undefined,
				confidence:
					typeof result.analysis.confidence === 'number' ? result.analysis.confidence : undefined,
				description:
					typeof result.analysis.description === 'string' ? result.analysis.description : undefined,
				name: typeof result.analysis.name === 'string' ? result.analysis.name : undefined,
				schedule: this.validateSchedule(result.analysis.schedule)
			};
		}

		return validated;
	}

	private validateSchedule(schedule: any): Record<string, string> | undefined {
		if (!schedule || typeof schedule !== 'object') {
			return undefined;
		}

		const validated: Record<string, string> = {};
		const validDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

		for (const day of validDays) {
			if (schedule[day] && typeof schedule[day] === 'string') {
				validated[day] = schedule[day];
			}
		}

		return Object.keys(validated).length > 0 ? validated : undefined;
	}

	async uploadScheduleData(
		analysisResult: AnalysisResult
	): Promise<{ success: boolean; message?: string }> {
		try {
			const response = await fetch(`${this.baseUrl}/save-schedule`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(analysisResult.analysis)
			});

			if (!response.ok) {
				throw new Error(`Failed to save schedule: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to upload schedule:', error);
			throw error;
		}
	}

	// Helper method to convert base64 to blob
	async base64ToBlob(base64: string): Promise<Blob> {
		const response = await fetch(base64);
		return await response.blob();
	}

	// Method to check API health
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
}

// Export singleton instance
export const apiService = new ApiService();
