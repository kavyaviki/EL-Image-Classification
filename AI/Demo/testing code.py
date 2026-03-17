#------------TESTING ------------
import torch
import timm
from torchvision import transforms
from PIL import Image

# ===== Settings =====
MODEL_PATH = "best_el_model.pth"
# IMAGE_PATH = r"D:\Akash\Dataset\Good EL Image\26356996.jpg"
IMAGE_PATH = r"D:\WorkingFolder\OneDrive - VikramGroup\D Drive\Projects\Project-13 EL Images solar\Code\Dataset\Good EL Image\26611020.jpg"
IMAGE_SIZE = 384
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

classes = ['defect','good']

# ===== Image Transform =====
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485,0.456,0.406],
        std=[0.229,0.224,0.225]
    )
])

# ===== Load Model =====
model = timm.create_model(
    "efficientnet_b3",
    pretrained=False,
    num_classes=2
)

model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model = model.to(DEVICE)
model.eval()

# ===== Test Function =====
def predict_image(image_path):

    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(image)
        probs = torch.softmax(output, dim=1)
        pred = torch.argmax(probs,1).item()

    print("Prediction :", classes[pred])
    print("Confidence :", float(probs[0][pred]))

# ===== Run Prediction =====
predict_image(IMAGE_PATH)