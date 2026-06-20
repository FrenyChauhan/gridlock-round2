# Modular Machine Learning Training Framework

A clean, reproducible, and configurable template for training Machine Learning models. This structure is built to separate data, experimental notebooks, production-grade source code, configurations, and serialized models.

## Folder Structure

```text
.
├── configs/
│   └── config.yaml            # Hyperparameters, paths, and configurations
├── data/                      # Local data directory (excluded from git tracking)
│   ├── raw/                   # Raw, unmodified source datasets
│   └── processed/             # Cleaned, standardized training splits
├── models/                    # Saved weights, training curves, and checkpoints
├── notebooks/                 # Jupyter notebooks for EDA and prototyping
├── src/                       # Source package for data pipelines and models
│   ├── __init__.py
│   ├── data_loader.py         # Ingests raw data, processes, and builds PyTorch loaders
│   ├── model.py               # Defines network architectures and baseline wrappers
│   ├── train.py               # Training loops, logging, and evaluation entry point
│   └── utils.py               # Helpers for seeding, config loading, and plotting
├── README.md                  # Project documentation
└── requirements.txt           # Python dependency lists
```

---

## Installation & Setup

1. **Create and Activate a Virtual Environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Quick Start & Verification

### Running the pipeline out-of-the-box
If you run the script immediately, it will auto-generate a mock classification dataset in `data/raw/` and execute training:
```bash
python src/train.py
```

### Swapping between PyTorch and Scikit-Learn
You can toggle between a Deep Learning model (PyTorch MLP) and Classical ML baseline models (Random Forest, Logistic Regression, etc.) by modifying the `configs/config.yaml` file:

```yaml
# configs/config.yaml
model:
  type: "pytorch" # Toggle to "scikit-learn" or "pytorch"
```

---

## Logging & Output
- **Model Checkpoints**: PyTorch checkpoints (`best_model.pth`) and Scikit-Learn pickle files (`model.pkl`) are stored in the `models/` folder.
- **Metrics & Visualization**: The PyTorch pipeline automatically saves validation/training loss graphs (`models/loss_curve.png`).
- **Logs**: Step-by-step logs are written to both stdout and a `training.log` file.
