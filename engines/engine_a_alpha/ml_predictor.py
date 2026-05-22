
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
from typing import Dict
import pickle
import os

class MLPredictor:
    """
    Tier 1 Feature: Machine Learning based signal generation.
    Uses Random Forest to predict probability of UP move (Binary Classification).
    
    Features:
    - Lagged Returns (1, 2, 3, 5 days)
    - Volatility (ATR, StdDev)
    - Momentum (RSI, ROC)
    - Volume Changes
    """
    
    def __init__(self, model_path: str = "data/models/rf_model.pkl") -> None:
        self.model_path = model_path
        self.model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=5, 
            min_samples_leaf=10, 
            random_state=42, 
            n_jobs=-1
        )
        self.is_trained = False
        
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create predictive features from OHLCV.
        """
        df = df.copy()
        
        # 1. Momentum / Transforms
        df['ret_1'] = df['Close'].pct_change()
        df['ret_5'] = df['Close'].pct_change(5)
        df['vol_20'] = df['ret_1'].rolling(20).std()
        df['rsi'] = self._rsi(df['Close'], 14)
        
        # 2. Volume dynamics
        df['vol_chg'] = df['Volume'].pct_change()
        
        # 3. Lagged features (The inputs for prediction)
        features = ['ret_1', 'ret_5', 'vol_20', 'rsi', 'vol_chg']
        cols = []
        for f in features:
            for lag in [1, 2]:
                col_name = f"{f}_lag{lag}"
                df[col_name] = df[f].shift(lag)
                cols.append(col_name)
                
        return df[cols].dropna()

    def _rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def train(self, data_map: Dict[str, pd.DataFrame]) -> None:
        """
        Train the model on historical data.
        Target: Next day return > 0 (1) else (0).
        """
        X_all = []
        y_all = []
        
        for tkr, df in data_map.items():
            if len(df) < 200: continue
            
            # Features
            features_df = self._engineer_features(df)
            
            # Target: Next day return positive?
            target = (df['Close'].pct_change().shift(-1) > 0).astype(int)
            
            # Align
            common_idx = features_df.index.intersection(target.index)
            X_part = features_df.loc[common_idx]
            y_part = target.loc[common_idx]
            
            X_all.append(X_part)
            y_all.append(y_part)
            
        if not X_all:
            print("[ML] No data to train on.")
            return
            
        X = pd.concat(X_all)
        y = pd.concat(y_all)
        
        # Train-Test Split (Time Series aware)
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Validate
        preds = self.model.predict(X_test)
        precision = precision_score(y_test, preds, zero_division=0)
        
        print(f"[ML] Trained Random Forest. Test Precision: {precision:.4f}")
        
        # Persist
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)
        except Exception as e:
            print(f"[ML] Failed to save model: {e}")

    def predict(self, df: pd.DataFrame) -> float:
        """
        Predict probability of Up move for the latest bar.
        Returns float 0.0 to 1.0.
        """
        if not self.is_trained:
            # Try load. T-067 (2026-05-22): narrow the bare-except per the
            # T-005/T-011/T-012 fail-loud-on-programmer-errors pattern.
            # Catch DATA/FILE errors only (corrupted pickle, ModuleNotFound
            # for old pickle classes, etc.); let programmer errors (TypeError,
            # NameError, AttributeError on local code) propagate.
            if os.path.exists(self.model_path):
                try:
                    with open(self.model_path, "rb") as f:
                        self.model = pickle.load(f)
                    self.is_trained = True
                except (
                    pickle.UnpicklingError,  # corrupted pickle
                    EOFError,                # truncated file
                    OSError,                 # disk / permission / unreadable
                    ImportError,             # pickle of class whose module moved
                    ModuleNotFoundError,     # ditto
                    MemoryError,             # bad length-prefix in corrupted pickle
                    ValueError,              # bad opcode / bad pickle structure
                ) as exc:
                    # File exists but unreadable — log + degrade to neutral
                    # probability (matches existing model-missing pathway).
                    import logging
                    logging.getLogger("MLPredictor").warning(
                        "[MLPredictor] model load failed for %s: %s",
                        self.model_path, exc,
                    )
                    return 0.5
            else:
                return 0.5
                
        features = self._engineer_features(df)
        if features.empty:
            return 0.5
            
        # Predict on last row
        last_row = features.iloc[[-1]]
        prob_up = self.model.predict_proba(last_row)[0][1] # Probability of class 1
        return prob_up
