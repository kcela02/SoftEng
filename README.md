# 📊 Predictive Sales & Restocking Dashboard System

## 📖 Description
The **Predictive Sales & Restocking Dashboard System** is a data-driven inventory management tool that leverages predictive algorithms to forecast product demand and optimize restocking schedules.  
The system integrates sales history, seasonal trends, and market patterns to generate accurate restocking recommendations.  

Using embedded forecasting algorithms (e.g., Regression models, ARIMA, or machine learning), the system helps businesses reduce overstock, prevent stockouts, and improve operational efficiency.  
The dashboard provides **real-time visualization** of sales performance, inventory status, and predictive analytics to support informed decision-making.

---

## 🎯 Objectives
- Automate sales forecasting using simple forecasting algorithms with at least **80% prediction accuracy** for the store’s top 10 best-selling products.  
- Optimize restocking schedules with an alert system that flags items projected to fall below a predefined stock threshold within the next 7 days.  
- Enhance decision-making through a **dashboard** that provides clear visualization of sales trends and inventory status.  
- Reduce inventory costs by providing actionable insights, minimizing manual restocking decisions.  
- Support business growth by building a **modular and scalable foundation** that can be expanded with advanced features in the future.  

---

## 📌 Scopes
- Process historical sales data manually uploaded via **CSV files**.  
- Utilize **Linear Regression** or **Moving Average models** to predict product demand.  
- Generate an **interactive, web-based dashboard** to represent sales trends, inventory levels, and demand forecasts.  
- Provide **automated, on-screen alerts** for low stock levels and restocking suggestions.  
- Produce **downloadable reports** on sales performance, inventory turnover, and forecasting accuracy.  

---

## ⚠️ Limitations
- Prediction accuracy depends on the **quality and completeness of historical data**.  
- May not account for **sudden, unpredictable market disruptions** (e.g., natural disasters, sudden demand spikes).  
- Less accurate for products with **highly erratic sales patterns**.  
- No direct integration with suppliers or external ordering systems.  
- Seasonal and regional variations require sufficient data to be modeled effectively.  

---

## 📂 Project Structure
```
predictive-dashboard/
│
├── data/                 # Sample sales CSV files and database schema
│   └── schema.sql        # SQL script for database setup
│
├── models/               # Forecasting algorithms (Regression, ARIMA, etc.)
│   ├── regression.py
│   ├── arima.py
│   └── utils.py
│
├── static/               # Frontend assets (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── img/
│
├── templates/            # HTML templates (for Flask/Django frontend)
│   ├── index.html
│   ├── dashboard.html
│   └── reports.html
│
├── reports/              # Exported PDF/CSV reports
│
├── app.py                # Main application entry point
├── config.py             # Database and system configuration
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/predictive-dashboard.git
cd predictive-dashboard
```

### 2️⃣ Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Database Setup
```bash
mysql -u root -p < data/schema.sql
```

### 5️⃣ Run the Application
```bash
python app.py
```

The system will be available at **http://127.0.0.1:5000/**  

---

## 🖥️ Usage
- Upload **CSV sales data** via the dashboard.  
- View **real-time charts** of sales, inventory, and forecasts.  
- Receive **automated alerts** for low stock items.  
- Download **reports** in CSV or PDF format.  

---

## 👨‍💻 Developers

This project was developed as a **Capstone Project** by a team of four.
 
| 👤 Developer | 🎓 Role | 💻 Skills | 🔗 GitHub | ✉️ Contact |
|--------------|---------|-----------|-----------|------------|
| **Ronan A. Gatmaitan** | Backend Developer | Python, Flask, MySQL | [github.com/ronan](https://github.com/ronanaleckgatmaitan=lab) | roananaleckgatmaitan@gmail.com |
| **Glenn G. Gamul** | Frontend Developer | HTML, CSS, JavaScript, Bootstrap | [github.com/Glenn](https://github.com/GUiSIPPE) | glennjimgamul@gmail.com |
| **Alberto C. Rili** | Data Analyst | Pandas, NumPy, ARIMA, Regression | [github.com/alberto](https://github.com/rcmtreb) | rcmtrebla@gmail.com.com |
| **Mark Angco** | Project Manager | Documentation, Git, System Design | [github.com/dev4](https://github.com/dev4) | dev4@example.com |




---

## 📜 License
This project is for **academic purposes only**. Not intended for commercial use.  
