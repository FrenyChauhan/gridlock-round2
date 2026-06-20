import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

class PyTorchMLP(nn.Module):
    """
    A simple Multi-Layer Perceptron for binary/multiclass classification.
    """
    def __init__(self, input_dim: int, hidden_dims: list, output_dim: int = 1, dropout: float = 0.2):
        super(PyTorchMLP, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = h_dim
            
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.network(x)

def get_scikit_learn_model(model_name: str, **kwargs):
    """
    Factory function to initialize a Scikit-Learn baseline classifier.
    """
    model_name = model_name.lower()
    
    if model_name == "random_forest":
        n_estimators = kwargs.get("n_estimators", 100)
        max_depth = kwargs.get("max_depth", None)
        return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        
    elif model_name == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=42)
        
    elif model_name == "gradient_boosting":
        n_estimators = kwargs.get("n_estimators", 100)
        max_depth = kwargs.get("max_depth", 3)
        return GradientBoostingClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        
    else:
        raise ValueError(f"Unknown Scikit-learn model type: {model_name}")
