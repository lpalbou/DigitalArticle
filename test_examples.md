# Test Examples for Digital Article

This document provides example prompts you can use to test the functionality of the Digital Article.

## Sample Data

The `sample_data/` directory contains:
- `sales_data.csv`: Sample sales data with products, categories, prices, quantities, and customer segments
- `customer_demographics.csv`: Customer demographic data with age, income, education, and region

## Example Prompts

### 1. Data Loading and Exploration

**Prompt:** "Load the sales data from sample_data/sales_data.csv and show me the first few rows"

**Expected Code:**
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the sales data
sales_data = pd.read_csv('sample_data/sales_data.csv')

# Display first few rows
print("Sales Data - First 5 rows:")
print(sales_data.head())

# Show basic info about the dataset
print("\nDataset Info:")
print(f"Shape: {sales_data.shape}")
print(f"Columns: {list(sales_data.columns)}")
```

### 2. Summary Statistics

**Prompt:** "Calculate summary statistics for the sales data, focusing on revenue and quantity"

**Expected Code:**
```python
# Summary statistics
print("Summary Statistics:")
print(sales_data.describe())

print("\nRevenue Statistics:")
print(f"Total Revenue: ${sales_data['revenue'].sum():,.2f}")
print(f"Average Revenue: ${sales_data['revenue'].mean():,.2f}")
print(f"Median Revenue: ${sales_data['revenue'].median():,.2f}")

print("\nQuantity Statistics:")
print(f"Total Quantity Sold: {sales_data['quantity'].sum():,}")
print(f"Average Quantity per Sale: {sales_data['quantity'].mean():.1f}")
```

### 3. Visualization - Revenue by Product

**Prompt:** "Create a bar chart showing total revenue by product"

**Expected Code:**
```python
# Calculate total revenue by product
revenue_by_product = sales_data.groupby('product')['revenue'].sum().sort_values(ascending=False)

# Create bar chart
plt.figure(figsize=(10, 6))
revenue_by_product.plot(kind='bar')
plt.title('Total Revenue by Product')
plt.xlabel('Product')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Print the data
print("Revenue by Product:")
for product, revenue in revenue_by_product.items():
    print(f"{product}: ${revenue:,.2f}")
```

### 4. Time Series Analysis

**Prompt:** "Show me the daily revenue trend over time"

**Expected Code:**
```python
# Convert date column to datetime
sales_data['date'] = pd.to_datetime(sales_data['date'])

# Calculate daily revenue
daily_revenue = sales_data.groupby('date')['revenue'].sum()

# Create line plot
plt.figure(figsize=(12, 6))
plt.plot(daily_revenue.index, daily_revenue.values, marker='o')
plt.title('Daily Revenue Trend')
plt.xlabel('Date')
plt.ylabel('Revenue ($)')
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Print daily totals
print("Daily Revenue:")
for date, revenue in daily_revenue.items():
    print(f"{date.strftime('%Y-%m-%d')}: ${revenue:,.2f}")
```

### 5. Customer Segment Analysis

**Prompt:** "Analyze revenue by customer segment and create a pie chart"

**Expected Code:**
```python
# Revenue by customer segment
segment_revenue = sales_data.groupby('customer_segment')['revenue'].sum()

# Create pie chart
plt.figure(figsize=(8, 8))
plt.pie(segment_revenue.values, labels=segment_revenue.index, autopct='%1.1f%%', startangle=90)
plt.title('Revenue Distribution by Customer Segment')
plt.axis('equal')
plt.show()

# Print segment analysis
print("Revenue by Customer Segment:")
total_revenue = segment_revenue.sum()
for segment, revenue in segment_revenue.items():
    percentage = (revenue / total_revenue) * 100
    print(f"{segment}: ${revenue:,.2f} ({percentage:.1f}%)")
```

### 6. Category Performance

**Prompt:** "Compare the performance of different product categories by both revenue and quantity sold"

**Expected Code:**
```python
# Category analysis
category_stats = sales_data.groupby('category').agg({
    'revenue': ['sum', 'mean'],
    'quantity': ['sum', 'mean'],
    'price': 'mean'
}).round(2)

# Flatten column names
category_stats.columns = ['_'.join(col).strip() for col in category_stats.columns]

print("Category Performance:")
print(category_stats)

# Create subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Revenue by category
category_revenue = sales_data.groupby('category')['revenue'].sum()
ax1.bar(category_revenue.index, category_revenue.values)
ax1.set_title('Total Revenue by Category')
ax1.set_ylabel('Revenue ($)')

# Quantity by category
category_quantity = sales_data.groupby('category')['quantity'].sum()
ax2.bar(category_quantity.index, category_quantity.values, color='orange')
ax2.set_title('Total Quantity by Category')
ax2.set_ylabel('Quantity')

plt.tight_layout()
plt.show()
```

### 7. Advanced Analytics - Customer Demographics

**Prompt:** "Load customer demographics data and analyze the relationship between age, income, and purchase frequency"

**Expected Code:**
```python
# Load customer demographics
customer_data = pd.read_csv('sample_data/customer_demographics.csv')

print("Customer Demographics:")
print(customer_data.head())
print(f"\nDataset shape: {customer_data.shape}")

# Create scatter plots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

# Age vs Purchase Frequency
ax1.scatter(customer_data['age'], customer_data['purchase_frequency'])
ax1.set_xlabel('Age')
ax1.set_ylabel('Purchase Frequency')
ax1.set_title('Age vs Purchase Frequency')

# Income vs Purchase Frequency
ax2.scatter(customer_data['income'], customer_data['purchase_frequency'])
ax2.set_xlabel('Income ($)')
ax2.set_ylabel('Purchase Frequency')
ax2.set_title('Income vs Purchase Frequency')

# Age distribution
ax3.hist(customer_data['age'], bins=10, edgecolor='black')
ax3.set_xlabel('Age')
ax3.set_ylabel('Count')
ax3.set_title('Age Distribution')

# Income distribution
ax4.hist(customer_data['income'], bins=10, edgecolor='black', color='green')
ax4.set_xlabel('Income ($)')
ax4.set_ylabel('Count')
ax4.set_title('Income Distribution')

plt.tight_layout()
plt.show()
```

### 8. Correlation Analysis

**Prompt:** "Calculate correlations between numeric variables in the customer data and create a heatmap"

**Expected Code:**
```python
import seaborn as sns

# Calculate correlation matrix
numeric_columns = ['age', 'income', 'purchase_frequency']
correlation_matrix = customer_data[numeric_columns].corr()

print("Correlation Matrix:")
print(correlation_matrix)

# Create heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, 
            square=True, fmt='.3f')
plt.title('Customer Demographics Correlation Matrix')
plt.tight_layout()
plt.show()
```

### 9. Regional Analysis

**Prompt:** "Analyze customer distribution and average income by region"

**Expected Code:**
```python
# Regional analysis
regional_stats = customer_data.groupby('region').agg({
    'customer_id': 'count',
    'income': ['mean', 'median'],
    'age': 'mean',
    'purchase_frequency': 'mean'
}).round(2)

# Flatten column names
regional_stats.columns = ['_'.join(col).strip() for col in regional_stats.columns]
regional_stats = regional_stats.rename(columns={'customer_id_count': 'customer_count'})

print("Regional Statistics:")
print(regional_stats)

# Create visualizations
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Customer count by region
customer_count = customer_data['region'].value_counts()
ax1.pie(customer_count.values, labels=customer_count.index, autopct='%1.1f%%')
ax1.set_title('Customer Distribution by Region')

# Average income by region
avg_income = customer_data.groupby('region')['income'].mean()
ax2.bar(avg_income.index, avg_income.values, color='skyblue')
ax2.set_title('Average Income by Region')
ax2.set_ylabel('Income ($)')

plt.tight_layout()
plt.show()
```

### 10. Interactive Plotly Visualization

**Prompt:** "Create an interactive scatter plot showing the relationship between age and income, colored by education level"

**Expected Code:**
```python
import plotly.express as px

# Create interactive scatter plot
fig = px.scatter(customer_data, 
                x='age', 
                y='income',
                color='education',
                size='purchase_frequency',
                hover_data=['region'],
                title='Customer Age vs Income by Education Level')

fig.update_layout(
    xaxis_title="Age",
    yaxis_title="Income ($)",
    width=800,
    height=600
)

fig.show()
```

## Testing Instructions

1. Start the backend server:
   ```bash
   python start_backend.py
   ```

2. Start the frontend:
   ```bash
   node start_frontend.js
   ```

3. Open your browser to `http://localhost:3000`

4. Create a new notebook and try the example prompts above

5. The LLM should generate appropriate Python code for each prompt that:
   - Loads the sample data correctly
   - Performs the requested analysis
   - Creates appropriate visualizations
   - Displays results in a user-friendly format

## Expected Behavior

- Prompts should generate executable Python code
- Code should run without errors (assuming sample data is available)
- Results should display properly in the result panels
- Plots should render as images or interactive visualizations
- Tables should display in a formatted table view
- Error messages should be clear and helpful if something goes wrong
