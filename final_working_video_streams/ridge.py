import cv2
import numpy as np

THRESHOLD = 150
BRIGHT = 0.7
DARK = 0.2

# Read grayscale image
img = cv2.imread("roi.jpg", cv2.IMREAD_GRAYSCALE)

# --- Enhancement stage (local contrast normalization style) ---
float_gray = img.astype(np.float32) / 255.0

blur = cv2.GaussianBlur(float_gray, (0, 0), 10)
num = float_gray - blur

blur_sq = cv2.GaussianBlur(num * num, (0, 0), 20)
den = np.sqrt(blur_sq)

# Avoid divide-by-zero
den[den == 0] = 1e-6

enhanced = num / den
enhanced = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
enhanced = enhanced.astype(np.uint8)

# --- Low-pass filter ---
gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3)

# --- High-pass via Laplacian ---
laplace = cv2.Laplacian(gaussian, cv2.CV_32F, ksize=19)

lapmin, lapmax, _, _ = cv2.minMaxLoc(laplace)
scale = 127 / max(-lapmin, lapmax)

laplace = (laplace * scale + 128).astype(np.uint8)

# --- Threshold to create mask ---
_, mask = cv2.threshold(laplace, THRESHOLD, 255, cv2.THRESH_BINARY)

# Morphological open
kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

# Morphological close
kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

# Smooth mask
mask = cv2.GaussianBlur(mask, (15, 15), 0)

# Slight smoothing of enhanced image
enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)

# --- Amplify veins using mask ---
coeff = (1.0 - (mask.astype(np.float32) / 255.0)) * BRIGHT + (1 - DARK)
result = coeff * enhanced.astype(np.float32)
result = np.clip(result, 0, 255).astype(np.uint8)

# --- Save enhanced output as image ---
cv2.imwrite("enhanced.jpg", result)

# --- Apply red color to amplified (vein) regions only ---
# Start with grayscale base
result_rgb = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
# Red overlay for vein regions (mask high = veins)
red_overlay = np.zeros_like(result_rgb)
red_overlay[:, :, 2] = 255  # BGR: red channel
mask_norm = (mask.astype(np.float32) / 255.0)[:, :, np.newaxis]
result_red_veins = (1 - mask_norm) * result_rgb.astype(np.float32) + mask_norm * red_overlay
result_red_veins = np.clip(result_red_veins, 0, 255).astype(np.uint8)

# Save red-vein visualization
cv2.imwrite("enhanced_red_veins.jpg", result_red_veins)

# --- Display ---
cv2.imshow("Original", img)
cv2.waitKey(0)

cv2.imshow("Enhanced", result)
cv2.waitKey(0)

cv2.imshow("Red Veins", result_red_veins)
cv2.waitKey(0)

cv2.destroyAllWindows()

