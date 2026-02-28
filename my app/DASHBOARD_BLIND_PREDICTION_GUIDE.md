# USING BLIND PREDICTIONS ON YOUR DASHBOARD
## Step-by-Step Guide to See Predicted vs Actual Sales (2023-Present)

---

## 🎯 What You'll Achieve

After running these steps, your dashboard will show:
- **Green Line**: Your actual sales (2023-2026)
- **Blue Line**: Blind predictions (made by pre-trained model)
- **Comparison**: How well the "adult" model predicted your real sales

---

## 🚀 Quick Start (3 Commands)

### **Step 1: Generate Baseline Training Data**
```bash
cd "e:\nanoR natiamtaG\thirdYear\SoftEng\my app"
python generate_baseline_training_data.py
```

**What happens**: Creates 3 years of synthetic sales data (2020-2022) for training

---

### **Step 2: Pre-Train Models**
```bash
python pretrain_model_on_baseline.py
```

**What happens**: Trains models ONLY on synthetic data, saves them to disk

---

### **Step 3: Generate Blind Predictions & Save to Database**
```bash
python blind_predict_actual_sales.py
```

**What happens**: 
- Pre-trained models predict your real sales WITHOUT seeing them first
- Saves predictions as `Forecast` records with `model_used='BLIND_PREDICTION'`
- These now appear on your dashboard!

---

## 📊 Viewing Results on Dashboard

### **Option 1: Check Forecast Trend Chart**
1. Open your dashboard: `http://127.0.0.1:5000`
2. Go to **Admin** tab
3. Look at **"Forecast Trend Analysis"** chart
4. You should now see:
   - **Green line**: Actual sales
   - **Blue dashed line**: Blind predictions
   - **Tooltip**: Shows accuracy when you hover over overlapping points

### **Option 2: Use New API Endpoint**
```javascript
// In browser console or via AJAX:
fetch('/api/blind-prediction-data?start_date=2023-01-01')
  .then(res => res.json())
  .then(data => console.log(data))
```

**Response**:
```json
{
  "success": true,
  "dates": ["2023-01-01", "2023-01-02", ...],
  "predicted": [45.2, 38.7, ...],
  "actual": [42, 40, ...],
  "accuracy": 87.3,
  "mae": 3.2,
  "note": "Predictions from pre-trained model"
}
```

---

## 🔍 Understanding the Results

### **What MAE Means**
```
MAE = Mean Absolute Error
MAE = Average difference between predicted and actual

Example:
  Predicted: 45 units
  Actual: 42 units
  Error: |45 - 42| = 3 units
  
If MAE = 3.2, the model is off by ±3 units on average
```

### **Accuracy Interpretation**
| Accuracy | Meaning | Recommendation |
|----------|---------|----------------|
| **> 90%** | 🟢 Excellent | Pre-trained model works! |
| **80-90%** | 🟡 Good | Usable, can fine-tune |
| **70-80%** | 🟠 Moderate | Needs real data |
| **< 70%** | 🔴 Poor | Retrain on real data |

---

## 🔄 How Your Daily Uploads Work

### **Before Blind Prediction System**
```
Upload CSV → Train on all real data → Generate forecasts → Show on dashboard
```

### **After Blind Prediction System**
```
Upload CSV → Train on all real data → Generate forecasts → Show on dashboard
            ↓
(SAME AS BEFORE - Nothing changed!)

PLUS (Optional/Separate):
Run blind_predict_actual_sales.py → See blind predictions on dashboard
```

**Your daily uploads continue working normally!**

The blind predictions are **additional** data showing:
- "What would the pre-trained model predict?"
- "How accurate are those predictions?"
- "Do we need more training data?"

---

## 📈 Example Visualization

After running the scripts, your **Forecast Trend Analysis** chart shows:

```
Revenue (₱)
│
│  ███  ═══  ███  ═══
│ ██░██═══ ██░██═══ ██   ← Green = Actual
│██░░░██══██░░░██══██    ← Blue = Blind Prediction
│░░░░░░██░░░░░░░░██░░
└────────────────────────→ Dates (2023-2026)
```

**Hover over any point**: "Blind Prediction: ₱45,230 | Actual: ₱42,150 | Accuracy: 93.2%"

---

## 🛠️ Advanced: Filtering by Product

### **View specific product's blind predictions**:
```bash
# In Python:
from app import app, db
from models import Forecast
from datetime import datetime

with app.app_context():
    # Get blind predictions for product ID 5
    forecasts = Forecast.query.filter(
        Forecast.product_id == 5,
        Forecast.model_used == 'BLIND_PREDICTION'
    ).order_by(Forecast.forecast_date).all()
    
    for f in forecasts[:10]:  # First 10 predictions
        print(f"{f.forecast_date}: Predicted {f.predicted_quantity} units")
```

### **Via API**:
```javascript
fetch('/api/blind-prediction-data?product_id=5&start_date=2023-01-01')
  .then(res => res.json())
  .then(data => console.log(data))
```

---

## ⚙️ Configuration

### **Change Prediction Period**
Edit `blind_predict_actual_sales.py` line 249:
```python
blind_predict_actual_sales(
    actual_start='2023-01-01',  # Start date
    actual_end='2026-02-28',    # End date
    save_to_database=True       # Save to dashboard
)
```

### **Retrain Pre-Trained Model**
If you want to retrain with different baseline data:
```bash
# 1. Delete old synthetic data
#    (manually via database tool or Python script)

# 2. Regenerate with new parameters
python generate_baseline_training_data.py

# 3. Retrain
python pretrain_model_on_baseline.py

# 4. Regenerate blind predictions
python blind_predict_actual_sales.py
```

---

## 🎓 What This Proves

### **The Experiment**:
1. ✅ Train "adult" model on Dataset A (synthetic 2020-2022)
2. ✅ Model predicts Dataset B (your real sales 2023-2026)
3. ✅ Model NEVER sees Dataset B before predicting
4. ✅ Compare predictions vs reality
5. ✅ Measure if synthetic training transfers to real world

### **Scientific Value**:
- **Transfer Learning Test**: Do patterns from A work on B?
- **Generalization Validation**: Does the model overfit or generalize?
- **Feature Importance**: Which features matter most?
- **Data Quality Check**: How realistic is synthetic data?

---

## 🗑️ Removing Blind Predictions

If you want to remove blind predictions and go back to normal:
```python
from app import app, db
from models import Forecast

with app.app_context():
    # Delete all blind prediction forecasts
    deleted = Forecast.query.filter(
        Forecast.model_used == 'BLIND_PREDICTION'
    ).delete()
    
    db.session.commit()
    print(f"Deleted {deleted} blind prediction forecasts")
```

Your dashboard will then show only the regular forecasts (trained on real data).

---

## 📞 Troubleshooting

### **"No blind prediction data found"**
**Cause**: Step 3 wasn't run or failed  
**Solution**: Run `python blind_predict_actual_sales.py` with `save_to_database=True`

### **"Insufficient data to run model"**
**Cause**: Steps 1 or 2 weren't completed  
**Solution**: Run steps 1 and 2 first

### **"Dashboard still shows old forecasts"**
**Cause**: Browser cache  
**Solution**: Hard refresh (Ctrl+Shift+R) or clear cache

### **"model_used column doesn't exist"**
**Cause**: Older database schema  
**Solution**: Check if `Forecast` table has `model_used` column. It should already exist.

---

## ✅ Verification Checklist

After running all steps, verify:
- [ ] `pretrained_baseline_models.pkl` file exists
- [ ] `blind_prediction_results.json` file exists  
- [ ] Database has `Sale` records with `is_synthetic=True` (baseline data)
- [ ] Database has `Forecast` records with `model_used='BLIND_PREDICTION'`
- [ ] Dashboard chart shows two lines (predicted + actual)
- [ ] API endpoint `/api/blind-prediction-data` returns data

---

## 📚 Files Created

| File | Purpose |
|------|---------|
| `generate_baseline_training_data.py` | Creates synthetic training data |
| `pretrain_model_on_baseline.py` | Trains models on synthetic data |
| `blind_predict_actual_sales.py` | Predicts real sales blindly |
| `pretrained_baseline_models.pkl` | Saved pre-trained models |
| `blind_prediction_results.json` | Validation metrics |

---

## 🎉 Success!

If you see both **green (actual)** and **blue (predicted)** lines on your dashboard showing data from 2023-present, you've successfully:

✅ Created a separate training dataset  
✅ Pre-trained models without seeing real data  
✅ Generated blind predictions for your actual sales  
✅ Visualized the comparison on your dashboard  
✅ Validated if synthetic-trained models generalize to reality  

**You've implemented scientific model validation!** 🎓

---

**Created**: February 28, 2026  
**System**: VapeCrib Dashboard - Blind Prediction Visualization
