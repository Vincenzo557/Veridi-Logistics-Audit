# Veridi Logistics — Delivery Performance Audit

> **Client:** Veridi Logistics (Global E-Commerce Aggregator)  
> **Dataset:** [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

---

## A. Executive Summary

Analysis of ~100,000 delivered Olist orders reveals that approximately **23% of orders arrive after the promised delivery date**, confirming the CEO's hypothesis that the platform is systematically over-promising. Late deliveries show a strong negative correlation with customer satisfaction — on-time orders average a review score of ~4.2/5, while "Super Late" orders (>5 days past estimate) drop to ~2.1/5, a 50% degradation. The problem is **not nationwide** — it is geographically concentrated: northern and northeastern states (AM, RR, AP, PA) have late-delivery rates 3–5× higher than southern hub states near São Paulo, pointing to last-mile carrier infrastructure gaps rather than a platform-wide failure. The ETA bias distribution shows signs of left-skew, suggesting the estimation algorithm is structurally optimistic and needs recalibration with state-specific buffers.

---

## B. Project Links

| Deliverable | Link |
|---|---|
| 📓 Notebook (Google Colab) | https://colab.research.google.com/drive/1Xuc3aLx22c2E6B5fKuasARVmj-G2NmKJ#scrollTo=tPL0_xhkyVm6 |
| 📊 Dashboard | https://dashboard-zbxgwlvjkhgs8mv7fyxtdn.streamlit.app/ |
| 🎨 Presentation (PDF) | Uploaded |


---

## C. Technical Explanation

### Data Cleaning

1. **Deduplication:** The `olist_order_reviews_dataset` contains multiple reviews per order (one-to-many). Before joining to `orders`, reviews were sorted by `review_creation_date` and deduplicated keeping the **first** review per `order_id`. This prevents row inflation that would skew all downstream aggregations.

2. **Undelivered Orders:** Orders with `order_status` of `canceled` or `unavailable` were excluded from the delay analysis and tracked separately. Orders missing `order_delivered_customer_date` were dropped (not imputed) — manufacturing a fake delivery date would distort the delay distribution.

3. **Date Parsing:** All five date columns were cast to `datetime64` via `pd.to_datetime()` before arithmetic operations.

4. **Join Integrity:** An assertion (`assert len(master) == len(orders)`) runs immediately after the joins to catch any accidental row duplication before analysis proceeds.

5. **Category Translation:** Product categories were translated from Portuguese to English using the official `product_category_name_translation.csv` mapping file. Orders with no matched category were retained with a `NaN` category value.

### Candidate's Choice — ETA Bias Distribution

**Feature:** A histogram of `days_difference` (estimated_delivery_date − actual_delivery_date) annotated with a skewness coefficient, alongside a monthly on-time rate trend line.

**Why it matters to the business:** Knowing *how many* orders are late is only half the story. The *shape* of the estimation error distribution answers a deeper question: **Is the ETA algorithm structurally biased?**

- A **left-skewed** distribution means the algorithm consistently sets optimistic estimates — it is systematically over-promising, and the fix is algorithmic (recalibrate ETAs with state-specific lag buffers).
- A **right-skewed** distribution means estimates are generally conservative, and the failures are isolated operational exceptions fixable through carrier SLA improvements.

The monthly trend line adds a temporal dimension — detecting whether performance is improving or degrading over time — which the CEO needs to know before committing budget to a fix.

---

## Repo Structure

```
├── veridi_logistics_audit.ipynb   # Main analysis notebook
├── veridi_logistics_audit.html    # Exported HTML of notebook (for GitHub preview)
├── streamlit_app.py               # Streamlit dashboard (deploy to Streamlit Cloud)
├── presentation.html              # Slide deck (8 slides, fully self-contained HTML)
├── README.md                      # This file
└── .gitignore                     # Excludes raw CSVs from the repo
```

**Note:** Raw CSV files are excluded from this repository via `.gitignore`. Download them directly from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place them in the project root before running the notebook.

---

## Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/veridi-logistics-audit.git
cd veridi-logistics-audit

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place Olist CSVs in the project root
# (download from Kaggle link above)

# 4. Run the notebook
jupyter notebook veridi_logistics_audit.ipynb

# 5. Run the dashboard
streamlit run streamlit_app.py
```

---

## Dependencies

See `requirements.txt`.
