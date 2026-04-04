import cv2
import numpy as np
import os

class AegisModel:
    """
    Ported from Aegis_3D simulation logic.
    Provides real CV-based crack detection and severity analysis.
    """
    @staticmethod
    def generate_crack_mask(image_path):
        """Auto-detect cracks and filter out background noise."""
        img = cv2.imread(image_path)
        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Use a bilateral filter to smooth noise while keeping edges sharp
        smoothed = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply a light Gaussian blur to filter out grain/texture noise
        blurred = cv2.GaussianBlur(smoothed, (5, 5), 0)
        
        # Adaptive thresholding — increased constant to 7 to reduce noise sensitivity
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY_INV, 15, 7)

        kernel = np.ones((3, 3), np.uint8)
        opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        final_mask = np.zeros_like(gray)
        
        if contours:
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            for cnt in contours[:10]:
                if cv2.contourArea(cnt) > 50:
                    cv2.drawContours(final_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                    cv2.drawContours(final_mask, [cnt], -1, 255, thickness=2)

        return final_mask

    @staticmethod
    def analyze_crack_properties(mask):
        """Analyze crack properties from mask."""
        if mask is None or np.sum(mask) == 0:
            return {"length": 0, "width": 0, "depth": 0, "severity_score": 0, "num_cracks": 0}

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {"length": 0, "width": 0, "depth": 0, "severity_score": 0, "num_cracks": 0}

        largest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest)

        length = max(rect[1][0], rect[1][1])
        width = min(rect[1][0], rect[1][1])

        crack_pixels = np.sum(mask > 0)
        total_pixels = mask.shape[0] * mask.shape[1]
        
        # Recalibrated multiplier (20 instead of 50) to match Aegis-3D baseline
        severity = min(crack_pixels / total_pixels * 20, 1.0) 

        # Return in a format compatible with Ignisia's risk engine
        return {
            "length": float(length),
            "width": float(max(width, 3)),
            "depth": float(length * 0.1),
            "severity_score": float(severity * 100), # 0-100 scale
            "num_cracks": len(contours),
        }

    @staticmethod
    def generate_depth_map(image_path, mask=None):
        """Generate a depth map from image."""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None

        depth = img.astype(np.float32) / 255.0
        depth_blurred = cv2.GaussianBlur(depth, (21, 21), 10)

        if mask is not None:
            mask_norm = mask.astype(np.float32) / 255.0
            depth_blurred = depth_blurred * (1.0 - mask_norm * 0.8)

        depth_uint8 = (depth_blurred * 255).astype(np.uint8)
        
        # Apply COLORMAP_JET to simulate stress levels (red = deep/high stress, blue = low)
        stress_view_bgr = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_JET)
        return stress_view_bgr

    @staticmethod
    def crackLength(L0, t): return L0 * (1 + 0.10 * t + 0.02 * t * t)
    @staticmethod
    def crackWidth(W0, t): return W0 * (1 + 0.08 * t + 0.015 * t * t)
    @staticmethod
    def crackDepth(D0, t): return D0 * (1 + 0.12 * t + 0.02 * t * t)

    @staticmethod
    def simulate_deterioration(image_path, mask, years=5):
        """
        Simulate structural deterioration after N years.
        Grows existing cracks and adds predicted branching.
        """
        img = cv2.imread(image_path)
        if img is None or mask is None:
            return None
        
        # 1. Grow existing crack width (using dilation)
        # 5 years of width growth typically results in ~1.7x width according to current model
        kernel_size = int(max(3, years * 1.5))
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        grown_mask = cv2.dilate(mask, kernel, iterations=1)
        
        # 2. Add predicted branches
        # Find contours of original crack to find branch points
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rng = np.random.default_rng(seed=42)
        
        deteriorated_mask = grown_mask.copy()
        if contours:
            for cnt in contours[:3]: # Only branch from major cracks
                # Pick a random point on a major contour
                if len(cnt) > 10:
                    for _ in range(years // 2): # Number of branches depends on years
                        idx = rng.integers(0, len(cnt))
                        pt = cnt[idx][0]
                        # Draw a random branch
                        length = rng.uniform(20, 80)
                        angle = rng.uniform(0, 2 * np.pi)
                        end_pt = (
                            int(pt[0] + np.cos(angle) * length),
                            int(pt[1] + np.sin(angle) * length)
                        )
                        cv2.line(deteriorated_mask, tuple(pt), end_pt, 255, thickness=rng.integers(2, 5))

        # 3. Apply to original image
        # Create a darkened version of the cracks on the image
        img_predicted = img.copy()
        # Set pixels where mask is white to a darker/cracked color
        img_predicted[deteriorated_mask > 0] = [30, 30, 30] # Dark crack color
        
        # Smooth the overlay slightly
        img_predicted = cv2.addWeighted(img, 0.4, img_predicted, 0.6, 0)

        return img_predicted
