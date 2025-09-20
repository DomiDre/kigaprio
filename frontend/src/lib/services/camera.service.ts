import type { CameraFacingMode } from '../types/scanner';

export class CameraService {
	private stream: MediaStream | null = null;

	async startCamera(facingMode: CameraFacingMode = 'environment'): Promise<MediaStream> {
		await this.stopCamera();

		const constraints: MediaStreamConstraints = {
			video: {
				facingMode,
				width: { ideal: 1920 },
				height: { ideal: 1080 }
			},
			audio: false
		};

		try {
			this.stream = await navigator.mediaDevices.getUserMedia(constraints);
		} catch {
			// Fallback to basic constraints
			this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
		}

		return this.stream;
	}

	async stopCamera(): Promise<void> {
		if (this.stream) {
			this.stream.getTracks().forEach((track) => track.stop());
			this.stream = null;
		}
	}

	async setupVideo(videoElement: HTMLVideoElement, stream: MediaStream): Promise<void> {
		videoElement.srcObject = stream;
		videoElement.setAttribute('autoplay', '');
		videoElement.setAttribute('muted', '');
		videoElement.setAttribute('playsinline', '');

		return new Promise((resolve) => {
			const handleReady = () => {
				videoElement
					.play()
					.then(() => resolve())
					.catch(() => resolve());
			};

			videoElement.onloadedmetadata = handleReady;
			if (videoElement.readyState >= 3) {
				handleReady();
			}
		});
	}

	capturePhoto(
		videoElement: HTMLVideoElement,
		canvas: HTMLCanvasElement,
		facingMode: CameraFacingMode
	): string {
		const ctx = canvas.getContext('2d');
		if (!ctx) throw new Error('Canvas context not available');

		const width = videoElement.videoWidth;
		const height = videoElement.videoHeight;

		canvas.width = width;
		canvas.height = height;

		if (facingMode === 'user') {
			ctx.translate(width, 0);
			ctx.scale(-1, 1);
		}

		ctx.drawImage(videoElement, 0, 0, width, height);
		return canvas.toDataURL('image/jpeg', 0.95);
	}

	isSupported(): boolean {
		return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
	}
}
