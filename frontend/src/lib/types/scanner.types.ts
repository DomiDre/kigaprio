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
	corners?: { x: number; y: number }[];
	confidence: number;
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

export type CameraFacingMode = 'user' | 'environment';

export interface ScannerState {
	cameraActive: boolean;
	capturedImage: string | null;
	isProcessing: boolean;
	analysisResult: AnalysisResult | null;
	error: string | null;
	paperDetected: boolean;
	detectionConfidence: number;
	captureCountdown: number;
}
