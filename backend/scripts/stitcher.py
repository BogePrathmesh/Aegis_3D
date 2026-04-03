import cv2
import numpy as np
import os
import uuid

def stitch_images(image_paths, output_folder):
    """
    Stitches a list of images into a single panoramic/orthomosaic image.
    :param image_paths: List of absolute file paths to the images.
    :param output_folder: Folder to save the stitched output.
    :return: Path to the stitched master image or None if stitching fails.
    """
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            images.append(img)
    
    if len(images) < 2:
        return image_paths[0] if image_paths else None

    # OpenCV Image Stitcher
    stitcher = cv2.Stitcher_create()
    status, stitched = stitcher.stitch(images)

    if status == cv2.STITCHER_OK:
        session_id = str(uuid.uuid4())[:8]
        output_filename = f"stitched_{session_id}.jpg"
        output_path = os.path.join(output_folder, output_filename)
        cv2.imwrite(output_path, stitched)
        return output_path
    else:
        print(f"Stitching failed with status code {status}")
        # If stitching fails, we fallback to the first image in the sequence 
        # or return None to let the API handle the error.
        return None
