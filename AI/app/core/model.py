# app/core/model.py
"""
Model loading, transforms, and prediction functions for EL image classification.
"""

import torch
import timm
from torchvision import transforms
from PIL import Image
import io
import os
import logging
from typing import Tuple, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────
#  Constants
# ────────────────────────────────────────────────
IMAGE_SIZE = 384
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLASSES = ["defect", "good"]  # Index 0: defect, Index 1: good

# Global variables (loaded once)
_model = None
_transform = None


def load_model(model_path: str = "best_el_model.pth") -> Tuple[any, transforms.Compose]:
    """
    Load the EfficientNet model once (singleton pattern).
    
    Args:
        model_path: Path to the model weights file
        
    Returns:
        Tuple of (model, transform)
        
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If model loading fails
    """
    global _model, _transform

    # Return cached model if already loaded
    if _model is not None and _transform is not None:
        logger.debug("Using cached model")
        return _model, _transform

    # Check if model file exists
    if not os.path.exists(model_path):
        abs_path = os.path.abspath(model_path)
        logger.error(f"Model file not found at: {abs_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Files in current directory: {[f for f in os.listdir('.') if f.endswith('.pth')]}")
        raise FileNotFoundError(f"Model file not found: {model_path}")

    logger.info(f"Loading model from {model_path} on device: {DEVICE}")
    
    try:
        # Create model architecture
        model = timm.create_model(
            "efficientnet_b3",
            pretrained=False,
            num_classes=2
        )

        # Load weights with proper error handling
        try:
            # Try safe loading first (weights_only=True)
            logger.info("Attempting to load with weights_only=True")
            state_dict = torch.load(model_path, map_location=DEVICE, weights_only=True)
        except Exception as e:
            logger.warning(f"weights_only=True failed: {e}. Trying without weights_only...")
            # Fallback to regular loading (less safe but more compatible)
            state_dict = torch.load(model_path, map_location=DEVICE)

        # Load state dict into model
        model.load_state_dict(state_dict)
        model = model.to(DEVICE)
        model.eval()

        # Create transform pipeline
        _transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        # Warmup inference (helps avoid first-prediction slowdown)
        try:
            logger.info("Running warmup inference...")
            dummy_input = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE, device=DEVICE)
            with torch.no_grad():
                _ = model(dummy_input)
            logger.info("Warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed but continuing: {e}")

        _model = model
        logger.info(f"Model loaded successfully. Device: {DEVICE}")
        
        return _model, _transform

    except FileNotFoundError:
        # Re-raise FileNotFoundError
        raise
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        raise RuntimeError(f"Model loading failed: {e}")


def predict_image(
    image_bytes: Union[bytes, io.BytesIO, str], 
    confidence_threshold: float = 0.7
) -> Tuple[str, float, bool]:
    """
    Run inference on image bytes (from file, S3, etc.)
    
    Args:
        image_bytes: Image as bytes, BytesIO object, or file path string
        confidence_threshold: Minimum confidence for reliable prediction
        
    Returns:
        Tuple of (prediction: str, confidence: float, above_threshold: bool)
        
    Raises:
        ValueError: If image is invalid
        RuntimeError: If inference fails
    """
    # Ensure torch is imported and available
    import torch
    
    try:
        # Load model (will use cached version if already loaded)
        model, transform = load_model()
        
        # Handle different input types
        if isinstance(image_bytes, str):
            # It's a file path
            with open(image_bytes, 'rb') as f:
                image_bytes = f.read()
        
        # Convert bytes to BytesIO if needed
        if isinstance(image_bytes, bytes):
            image_bytes = io.BytesIO(image_bytes)
        
        # Open and validate image
        try:
            image = Image.open(image_bytes)
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")
        
        # Convert to RGB if needed
        if image.mode != "RGB":
            logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert("RGB")
        
        # Apply transforms
        try:
            tensor = transform(image).unsqueeze(0).to(DEVICE)
        except Exception as e:
            raise ValueError(f"Failed to transform image: {e}")
        
        # Run inference
        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)
            pred_idx = int(torch.argmax(probs, dim=1))
            confidence = float(probs[0, pred_idx])
        
        # Get prediction label
        prediction = CLASSES[pred_idx]
        above_threshold = confidence >= confidence_threshold
        
        logger.debug(f"Prediction: {prediction}, Confidence: {confidence:.4f}, Above threshold: {above_threshold}")
        
        return prediction, confidence, above_threshold
        
    except FileNotFoundError:
        # Re-raise FileNotFoundError
        raise
    except ValueError:
        # Re-raise ValueError
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise RuntimeError(f"Inference failed: {e}")


def get_model_info() -> dict:
    """
    Get information about the loaded model.
    
    Returns:
        Dictionary with model information
    """
    try:
        model, _ = load_model()  # This will load if not already loaded
        
        info = {
            "device": DEVICE,
            "classes": CLASSES,
            "image_size": IMAGE_SIZE,
            "model_loaded": model is not None,
            "model_type": "EfficientNet-B3"
        }
        
        # Add parameter count if model is loaded
        if model is not None:
            try:
                param_count = sum(p.numel() for p in model.parameters())
                info["parameters"] = param_count
            except:
                pass
        
        return info
    except Exception as e:
        return {
            "error": str(e),
            "device": DEVICE,
            "model_loaded": False
        }


# Optional: Test function
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test model loading
    try:
        model, transform = load_model()
        print("✓ Model loaded successfully")
        print(f"  Device: {DEVICE}")
        print(f"  Classes: {CLASSES}")
        
        # Test prediction on a dummy image
        print("\nTesting dummy prediction...")
        dummy_bytes = io.BytesIO()
        from PIL import Image
        import numpy as np
        dummy_img = Image.fromarray(np.random.randint(0, 255, (384, 384, 3), dtype=np.uint8))
        dummy_img.save(dummy_bytes, format='JPEG')
        
        pred, conf, above = predict_image(dummy_bytes.getvalue())
        print(f"  Prediction: {pred}")
        print(f"  Confidence: {conf:.4f}")
        print(f"  Above threshold: {above}")
        
    except Exception as e:
        print(f"✗ Error: {e}")