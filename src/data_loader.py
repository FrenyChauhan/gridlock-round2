import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Try importing torch-related classes
try:
    import torch
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    # Fallback placeholders if torch is not yet installed
    class Dataset:
        pass
    class DataLoader:
        pass

def generate_mock_data(n_samples: int = 1200, n_features: int = 10, output_dir: str = "data/raw"):
    """
    Generate a synthetic binary classification dataset and save it as raw csv files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate random features
    X = np.random.randn(n_samples, n_features)
    
    # Create a simple non-linear decision boundary for classification
    # target = 1 if sum of first 3 features + some noise > 0 else 0
    noise = np.random.normal(0, 0.5, n_samples)
    logit = X[:, 0] + 1.5 * X[:, 1] - 0.8 * X[:, 2] + noise
    y = (logit > 0).astype(int)
    
    # Combine into DataFrame
    columns = [f"feature_{i}" for i in range(n_features)]
    df = pd.DataFrame(X, columns=columns)
    df["target"] = y
    
    # Save raw data
    raw_path = os.path.join(output_dir, "raw_data.csv")
    df.to_csv(raw_path, index=False)
    print(f"Generated mock raw data at {raw_path}")
    return raw_path

def preprocess_data(raw_dir: str, processed_dir: str, target_col: str, test_size: float = 0.2, random_seed: int = 42):
    """
    Load raw data, perform train/test splitting, normalize features, and save processed splits.
    """
    os.makedirs(processed_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "raw_data.csv")
    if not os.path.exists(raw_path):
        print("Raw data not found. Generating mock data first...")
        generate_mock_data(output_dir=raw_dir)
        
    df = pd.read_csv(raw_path)
    
    # Separate features and target
    X = df.drop(columns=[target_col])
    y = df[target_col]
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_seed, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Recombine and save
    train_df = pd.DataFrame(X_train_scaled, columns=X.columns)
    train_df[target_col] = y_train.values
    
    test_df = pd.DataFrame(X_test_scaled, columns=X.columns)
    test_df[target_col] = y_test.values
    
    train_path = os.path.join(processed_dir, "train.csv")
    test_path = os.path.join(processed_dir, "test.csv")
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"Preprocessed and saved split data to: \n  - {train_path}\n  - {test_path}")
    return train_path, test_path

class TabularDataset(Dataset):
    """
    Custom PyTorch Dataset for loading tabular data.
    """
    def __init__(self, csv_file: str, target_col: str):
        df = pd.read_csv(csv_file)
        self.X = df.drop(columns=[target_col]).values.astype(np.float32)
        self.y = df[target_col].values.astype(np.float32)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        # PyTorch expects tensors, but we convert in __getitem__ or at load-time
        return torch.tensor(self.X[idx]), torch.tensor(self.y[idx])

def get_pytorch_dataloaders(train_path: str, test_path: str, target_col: str, batch_size: int = 32):
    """
    Create train and validation PyTorch DataLoader objects.
    """
    train_dataset = TabularDataset(train_path, target_col)
    test_dataset = TabularDataset(test_path, target_col)
    
    # Split train further into train/val
    train_size = int(0.85 * len(train_dataset))
    val_size = len(train_dataset) - train_size
    
    # Use torch's random_split if available, else standard index split
    try:
        train_subset, val_subset = torch.utils.data.random_split(
            train_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42)
        )
    except NameError:
        # Fallback if torch is not installed
        raise ImportError("PyTorch must be installed to create DataLoaders.")
        
    train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_subset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader, test_loader
