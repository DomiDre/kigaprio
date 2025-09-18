export const SCANNER_CONFIG = {
	// Camera configuration
	camera: {
		defaultFacingMode: 'environment' as const,
		videoConstraints: {
			ideal: {
				width: 1920,
				height: 1080
			},
			fallback: {
				width: 640,
				height: 480
			}
		}
	},

	// Detection configuration
	detection: {
		minConfidence: 60,
		minAreaRatio: 0.2,
		targetAspectRatio: 1.41, // A4 paper ratio
		edgeThreshold: 30,
		cannyThresholds: {
			low: 50,
			high: 150
		},
		gaussianKernelSize: 5,
		contourApproximation: 0.02
	},

	// Auto-capture configuration
	autoCapture: {
		enabled: true,
		delay: 2000, // milliseconds
		minConfidence: 70,
		countdownInterval: 1000
	},

	// API configuration
	api: {
		baseUrl: '/api',
		timeout: 30000, // milliseconds
		retryAttempts: 3,
		retryDelay: 1000
	},

	// UI configuration
	ui: {
		animations: {
			fadeIn: 300,
			fadeOut: 200
		},
		messages: {
			cameraNotSupported: 'Camera API is not supported in your browser',
			cameraAccessDenied: 'Camera access was denied. Please grant permission and try again.',
			analysisError: 'Failed to analyze the image. Please try again.',
			networkError: 'Network error. Please check your connection and try again.'
		}
	},

	// OpenCV configuration
	opencv: {
		scriptUrl: 'https://docs.opencv.org/4.5.0/opencv.js',
		loadTimeout: 10000, // milliseconds
		checkInterval: 100
	}
};
