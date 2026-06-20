import os
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from src.utils import set_seed, load_config, setup_logging, plot_training_curves
from src.data_loader import preprocess_data, get_pytorch_dataloaders
from src.model import PyTorchMLP, get_scikit_learn_model

def train_pytorch(config, logger):
    """
    Train a PyTorch Multi-Layer Perceptron model.
    """
    logger.info("Initializing PyTorch training pipeline...")
    
    # 1. Hyperparameters & Settings
    train_cfg = config["training"]
    model_cfg = config["model"]["pytorch"]
    log_cfg = config["logging"]
    
    device = torch.device(train_cfg["device"] if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    
    # 2. Prepare Data Loaders
    train_path = config["data"]["train_path"]
    test_path = config["data"]["test_path"]
    target_col = config["data"]["target_column"]
    
    train_loader, val_loader, test_loader = get_pytorch_dataloaders(
        train_path=train_path,
        test_path=test_path,
        target_col=target_col,
        batch_size=train_cfg["batch_size"]
    )
    logger.info("PyTorch DataLoaders initialized successfully.")
    
    # 3. Initialize Model
    model = PyTorchMLP(
        input_dim=model_cfg["input_dim"],
        hidden_dims=model_cfg["hidden_dims"],
        output_dim=model_cfg["output_dim"],
        dropout=model_cfg["dropout"]
    ).to(device)
    logger.info(f"Model Architecture:\n{model}")
    
    # 4. Loss & Optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(
        model.parameters(), 
        lr=train_cfg["learning_rate"], 
        weight_decay=train_cfg["weight_decay"]
    )
    
    # 5. Training Loop
    epochs = train_cfg["epochs"]
    best_val_loss = float('inf')
    train_losses = []
    val_losses = []
    
    logger.info("Starting training...")
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_train_loss = 0.0
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            
            epoch_train_loss += loss.item() * X_batch.size(0)
            
        epoch_train_loss /= len(train_loader.dataset)
        train_losses.append(epoch_train_loss)
        
        # Validation evaluation
        model.eval()
        epoch_val_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                epoch_val_loss += loss.item() * X_batch.size(0)
                
                # Accuracy tracking
                preds = (torch.sigmoid(outputs) > 0.5).float()
                correct += (preds == y_batch).sum().item()
                total += y_batch.size(0)
                
        epoch_val_loss /= len(val_loader.dataset)
        val_losses.append(epoch_val_loss)
        val_acc = correct / total
        
        if epoch % log_cfg["log_interval"] == 0 or epoch == 1 or epoch == epochs:
            logger.info(
                f"Epoch {epoch}/{epochs} | "
                f"Train Loss: {epoch_train_loss:.4f} | "
                f"Val Loss: {epoch_val_loss:.4f} | "
                f"Val Acc: {val_acc:.4%}"
            )
            
        # Checkpoint Saving
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            model_dir = log_cfg["model_dir"]
            os.makedirs(model_dir, exist_ok=True)
            checkpoint_path = os.path.join(model_dir, log_cfg["model_name"])
            torch.save(model.state_dict(), checkpoint_path)
            logger.debug(f"Saved best model checkpoint to {checkpoint_path}")
            
    logger.info("Training complete.")
    
    # 6. Plot Loss Curve
    loss_plot_path = os.path.join(log_cfg["model_dir"], "loss_curve.png")
    plot_training_curves(train_losses, val_losses, output_path=loss_plot_path)
    logger.info(f"Loss curve plotted to {loss_plot_path}")
    
    # 7. Evaluate on Test Set
    logger.info("Evaluating best model on Test Set...")
    checkpoint_path = os.path.join(log_cfg["model_dir"], log_cfg["model_name"])
    model.load_state_dict(torch.load(checkpoint_path))
    model.eval()
    
    test_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            test_loss += loss.item() * X_batch.size(0)
            
            preds = (torch.sigmoid(outputs) > 0.5).float()
            correct += (preds == y_batch).sum().item()
            total += y_batch.size(0)
            
    test_loss /= len(test_loader.dataset)
    test_acc = correct / total
    logger.info(f"Test Loss: {test_loss:.4f} | Test Accuracy: {test_acc:.4%}")

def train_scikit_learn(config, logger):
    """
    Train a Scikit-Learn baseline classifier.
    """
    logger.info("Initializing Scikit-Learn training pipeline...")
    
    # 1. Hyperparameters & Settings
    model_cfg = config["model"]["scikit_learn"]
    log_cfg = config["logging"]
    target_col = config["data"]["target_column"]
    
    # 2. Load Processed Splits
    train_path = config["data"]["train_path"]
    test_path = config["data"]["test_path"]
    
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    X_train = train_df.drop(columns=[target_col]).values
    y_train = train_df[target_col].values
    
    X_test = test_df.drop(columns=[target_col]).values
    y_test = test_df[target_col].values
    
    # 3. Initialize Model
    model = get_scikit_learn_model(
        model_name=model_cfg["classifier"],
        n_estimators=model_cfg["n_estimators"],
        max_depth=model_cfg["max_depth"]
    )
    logger.info(f"Initialized Scikit-Learn model: {model}")
    
    # 4. Train Model
    logger.info("Fitting Scikit-Learn model...")
    model.fit(X_train, y_train)
    
    # 5. Evaluate Model
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    logger.info(f"Train Accuracy: {train_acc:.4%}")
    logger.info(f"Test Accuracy: {test_acc:.4%}")
    
    # 6. Save Model Checkpoint
    model_dir = log_cfg["model_dir"]
    os.makedirs(model_dir, exist_ok=True)
    checkpoint_path = os.path.join(model_dir, log_cfg["sklearn_model_name"])
    
    with open(checkpoint_path, 'wb') as file:
        pickle.dump(model, file)
    logger.info(f"Saved trained Scikit-learn model checkpoint to {checkpoint_path}")

def main():
    # Setup config path
    config_path = "configs/config.yaml"
    config = load_config(config_path)
    
    # Setup logger
    logger = setup_logging()
    
    # Set seed
    set_seed(config["training"]["random_seed"])
    logger.info(f"Random seed set to {config['training']['random_seed']}.")
    
    # Preprocess/Generate dataset
    preprocess_data(
        raw_dir=config["data"]["raw_dir"],
        processed_dir=config["data"]["processed_dir"],
        target_col=config["data"]["target_column"],
        random_seed=config["training"]["random_seed"]
    )
    
    # Select which framework pipeline to run
    model_type = config["model"]["type"].lower()
    if model_type == "pytorch":
        train_pytorch(config, logger)
    elif model_type == "scikit-learn":
        train_scikit_learn(config, logger)
    else:
        logger.error(f"Unsupported model type in config: {model_type}")
        raise ValueError(f"Unsupported model type: {model_type}")

if __name__ == "__main__":
    main()
