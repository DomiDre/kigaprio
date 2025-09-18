/**
 * Debounce function to limit execution rate
 */
export function debounce<T extends (...args: any[]) => any>(
	func: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	return function(this: any, ...args: Parameters<T>) {
		const context = this;

		if (timeoutId !== null) {
			clearTimeout(timeoutId);
		}

		timeoutId = setTimeout(() => {
			func.apply(context, args);
			timeoutId = null;
		}, wait);
	};
}

/**
 * Throttle function to limit execution rate
 */
export function throttle<T extends (...args: any[]) => any>(
	func: T,
	limit: number
): (...args: Parameters<T>) => void {
	let inThrottle: boolean = false;

	return function(this: any, ...args: Parameters<T>) {
		const context = this;

		if (!inThrottle) {
			func.apply(context, args);
			inThrottle = true;

			setTimeout(() => {
				inThrottle = false;
			}, limit);
		}
	};
}

/**
 * Calculate image dimensions to fit within constraints
 */
export function calculateImageDimensions(
	sourceWidth: number,
	sourceHeight: number,
	maxWidth: number,
	maxHeight: number
): { width: number; height: number } {
	const aspectRatio = sourceWidth / sourceHeight;

	let width = sourceWidth;
	let height = sourceHeight;

	if (width > maxWidth) {
		width = maxWidth;
		height = width / aspectRatio;
	}

	if (height > maxHeight) {
		height = maxHeight;
		width = height * aspectRatio;
	}

	return {
		width: Math.round(width),
		height: Math.round(height)
	};
}

/**
 * Convert base64 to File object
 */
export async function base64ToFile(
	base64: string,
	filename: string,
	mimeType: string = 'image/jpeg'
): Promise<File> {
	const response = await fetch(base64);
	const blob = await response.blob();
	return new File([blob], filename, { type: mimeType });
}

/**
 * Compress image to reduce file size
 */
export async function compressImage(
	base64: string,
	maxWidth: number = 1920,
	quality: number = 0.85
): Promise<string> {
	return new Promise((resolve, reject) => {
		const img = new Image();

		img.onload = () => {
			const canvas = document.createElement('canvas');
			const ctx = canvas.getContext('2d');

			if (!ctx) {
				reject(new Error('Canvas context not available'));
				return;
			}

			const { width, height } = calculateImageDimensions(
				img.width,
				img.height,
				maxWidth,
				maxWidth * 0.75 // Maintain aspect ratio
			);

			canvas.width = width;
			canvas.height = height;

			ctx.drawImage(img, 0, 0, width, height);

			resolve(canvas.toDataURL('image/jpeg', quality));
		};

		img.onerror = () => reject(new Error('Failed to load image'));
		img.src = base64;
	});
}

/**
 * Check if device has camera support
 */
export function hasCameraSupport(): boolean {
	return !!(
		navigator.mediaDevices &&
		navigator.mediaDevices.getUserMedia &&
		navigator.mediaDevices.enumerateDevices
	);
}

/**
 * Get available cameras
 */
export async function getAvailableCameras(): Promise<MediaDeviceInfo[]> {
	if (!hasCameraSupport()) {
		return [];
	}

	try {
		const devices = await navigator.mediaDevices.enumerateDevices();
		return devices.filter(device => device.kind === 'videoinput');
	} catch (error) {
		console.error('Failed to enumerate devices:', error);
		return [];
	}
}

/**
 * Format schedule time for display
 */
export function formatScheduleTime(time: string | undefined): string {
	if (!time) return '-';

	// Add any time formatting logic here
	// e.g., convert 24h to 12h format, add AM/PM, etc.
	return time;
}

/**
 * Validate schedule data
 */
export function validateScheduleData(schedule: Record<string, string>): boolean {
	const requiredDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

	return requiredDays.every(day =>
		schedule[day] && schedule[day].length > 0
	);
}

/**
 * Generate unique ID
 */
export function generateId(): string {
	return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Browser compatibility check
 */
export function checkBrowserCompatibility(): {
	compatible: boolean;
	issues: string[];
} {
	const issues: string[] = [];

	if (!hasCameraSupport()) {
		issues.push('Camera API not supported');
	}

	if (!window.Worker) {
		issues.push('Web Workers not supported');
	}

	if (!window.fetch) {
		issues.push('Fetch API not supported');
	}

	const canvas = document.createElement('canvas');
	if (!canvas.getContext('2d')) {
		issues.push('Canvas 2D context not supported');
	}

	return {
		compatible: issues.length === 0,
		issues
	};
}
