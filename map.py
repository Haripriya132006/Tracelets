# import cv2
# import matplotlib.pyplot as plt

# # Load the map
# img = cv2.imread("image.png")

# # 1. Convert to grayscale
# gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# # 2. Denoise slightly
# blur = cv2.GaussianBlur(gray, (5,5), 0)

# # 3. Apply adaptive threshold (better for uneven lighting)
# thresh = cv2.adaptiveThreshold(
#     blur, 255,
#     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#     cv2.THRESH_BINARY_INV,
#     11, 2
# )

# # 4. Edge detection (to extract walls/corridors)
# edges = cv2.Canny(thresh, 50, 150, apertureSize=3)

# # Show results
# plt.figure(figsize=(15,5))

# plt.subplot(1,3,1)
# plt.title("Gray")
# plt.imshow(gray, cmap='gray')

# plt.subplot(1,3,2)
# plt.title("Thresholded")
# plt.imshow(thresh, cmap='gray')

# plt.subplot(1,3,3)
# plt.title("Edges")
# plt.imshow(edges, cmap='gray')

# plt.show()

import cv2
import pytesseract

# If you're on Windows, set the tesseract.exe path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load image
img = cv2.imread("image.png")

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Threshold (improves OCR results)
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

# OCR
text = pytesseract.image_to_string(thresh)

# Split into lines & filter
rooms = [line.strip() for line in text.split("\n") if line.strip()]

print("Detected Rooms / Labels:")
for r in rooms:
    print(r)

