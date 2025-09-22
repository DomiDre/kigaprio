export interface AnalysisResult {
	success: boolean;
	analysis?: {
		labels?: string[];
		confidence?: number;
		description?: string;
		name?: string;
		schedule?: Record<string, string>;
	};
	error?: string;
}

export interface DetectionResult {
	detected: boolean;
	confidence: number;
	corners?: { x: number; y: number }[];
	stabilized?: boolean; // Added for stabilization status
}

export interface PaperDetectionConfig {
	minConfidence: number;
	minAreaRatio: number;
	maxAreaRatio: number;
	targetAspectRatio: number;
	autoCaptureDelay: number;
	edgeThreshold: number;
	minContourArea: number;
	cannyLower: number;
	cannyUpper: number;
}

export interface ScannerState {
	cameraActive: boolean;
	capturedImage: string | null;
	isProcessing: boolean;
	analysisResult: any | null;
	error: string | null;
	paperDetected: boolean;
	detectionConfidence: number;
	captureCountdown: number;
}

export type CameraFacingMode = 'user' | 'environment';
